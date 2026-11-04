"""CARD-338 AC-2, the half the re-cut did not measure: **how faithful is this
instrument to the end state it stands up?**

Not a test and not under ``tests/`` (G-2). Run from the worktree root::

    python scratchpad/card338/fidelity_to_the_end_state.py tests/test_book_pdf.py

**AC-2, as it now reads**, asks for *"the per-module failed+error counts … with
the ``delitem`` residue split out as its own column and the sites named — and
… reported as a share OF the conversion's cost, not as a probe artefact
deducted from it"*. **This script is the reason it reads that way.** The
question it was built to settle is kept below in the form it was asked, because
that is what the experiment tested — but it is SETTLED, and the answer is
recorded beside it so the question is not re-read as open.

**Asked.** AC-2 once asked for the probe's own shadow to be split out of the
census. The re-cut pass named one shadow — the ``KeyError`` from
``monkeypatch.delitem`` sites without ``raising=False`` — and bounded it at
≤13. **A shadow is a red the conversion would not produce**, so the only way to
know whether a red is one is to stand the conversion up a second way, without
the probe, and compare. That is what this script does.

**Answered, and it went the other way: the artefact is 0.** The counts agree on
a tree whose five entries are deleted in ``src/`` with no probe loaded, so those
13 reds are the CONVERSION's residue and not the probe's shadow. That is why
``census_five_kinds.py`` renamed its own column from ``artefact`` to ``delitem``
and prints it beside a ``conversion=`` that is the FULL red count, and why the
constant below is ``DELITEM``; it was named for the refuted framing until
CARD-338's fix round 2 (cycle-2 M-101) — the same rename for the same reason,
one instrument later. The printed verdict at the end of this script has always
said this; only this docstring and that constant still carried the old framing.

Three trees, each a copy of ``src/`` mutated on disk and imported in place of
the real one via ``-o pythonpath=`` (``src/`` itself is never edited — G-1):

* **E0 — as committed.** The control.
* **E1 — the five declarations deleted, nothing else.** CARD-322's item 1 taken
  literally: *"delete that kind's entry from ``_RASTER_DECLARATIONS``"*, with
  the generator's default writer set left as ``NO_DOWNSTREAM_WRITERS``. Every
  ``BookPDFGenerator(book)`` a test builds still has no downstream writers.
* **E2 — the five deleted AND the default writer set assembled.** What this
  card's probe simulates in-process.

The comparison answers two questions a downstream card is pricing against:

1. **Is the ``delitem`` ``KeyError`` really the instrument's shadow?** Under E1
   and E2 the key is absent from the module's own dict, so a test that pops it
   raises the same ``KeyError`` with no probe anywhere. If the counts agree,
   those reds are **residue the conversion owns**, not the probe's, and a card
   that discounts them is under-priced. **Measured: they agree, so they are
   residue — see "Answered" above. This question is closed.**
2. **What does the writer rebinding itself move?** E2 minus E1 is exactly the
   rebinding's effect, which is the shadow this card's own extension adds and
   the one nobody has bounded.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python")
HERE = Path(__file__).resolve().parent
SCRATCH = Path(
    os.environ.get(
        "CARD338_SCRATCH",
        # Session-INDEPENDENT by construction (CARD-338 fix round 2, cycle-2
        # M-104). This defaulted to one authoring session's ephemeral
        # ``/private/tmp/claude-501/.../<session uuid>/`` path, and three cards
        # tell a reader to run this instrument. The path is
        # ``mkdir(parents=True)``-ed, so a later run never crashed -- it wrote
        # mutated copies of ``src/`` into a FOREIGN session's directory, and the
        # override was discoverable only by reading this line.
        #
        # ``gettempdir()`` honours ``TMPDIR``, which macOS sets per-user, so the
        # default is private without being tied to one run; the worktree's own
        # directory name keeps two worktrees' trees apart. Deterministic rather
        # than ``mkdtemp()`` on purpose: these mutated trees are meant to be
        # inspectable after the run, and this script removes its own.
        str(Path(tempfile.gettempdir()) / f"card338-scratch-{ROOT.name}"),
    )
)
GENERATOR = "src/nonogram/admin/book_pdf_generator.py"
KINDS = ("PUZZLE", "TITLE", "GUIDE", "TOC", "ANSWER")

COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed)")
TB_LINE = re.compile(r"^(/?\S*\.py):(\d+): (.*)$", re.M)
DELITEM = re.compile(r"monkeypatch\.py:\d+: KeyError: <PageKind\.")


def sweep(where: Path) -> None:
    for cache in where.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def tree(name: str, *, drop: bool, assemble: bool) -> Path:
    into = SCRATCH / "fidelity" / name
    if into.exists():
        shutil.rmtree(into)
    into.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "src", into / "src")
    tail = []
    if drop:
        tail.append(
            "\n\n# CARD-338 fidelity: the five kinds CARD-322 converts, deleted\n"
            "# from the registry on disk -- the end state, not a session mutation.\n"
            + "".join(
                f"_RASTER_DECLARATIONS.pop(PageKind.{kind}, None)\n" for kind in KINDS
            )
        )
    if assemble:
        tail.append(
            "\n# CARD-338 fidelity: the generator's default writer set is the\n"
            "# assembly point's full set, which is what the probe rebinds.\n"
            "from nonogram.admin import book_interior_vector as _assembly\n"
            "NO_DOWNSTREAM_WRITERS = _assembly.DOWNSTREAM_WRITERS\n"
        )
    if tail:
        path = into / GENERATOR
        path.write_text(path.read_text() + "".join(tail))
    sweep(into)
    return into


def run(target: str, *, src: Path | None, probe: str | None) -> tuple[dict, int, int]:
    sweep(ROOT)
    argv = [str(PYTHON), "-m", "pytest", "-o", "addopts=", "-q", "-rfs", "--tb=line"]
    if src is not None:
        argv += ["-o", f"pythonpath={src / 'src'}"]
    if probe:
        argv += ["-p", probe]
    argv.append(target)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(HERE))
    done = subprocess.run(
        argv, cwd=str(ROOT), env=env, capture_output=True, text=True
    )
    out = done.stdout + done.stderr
    sweep(ROOT)
    counts = {word: int(number) for number, word in COUNT.findall(out)}
    collected = sum(
        counts.get(key, 0)
        for key in ("passed", "failed", "error", "errors", "skipped",
                    "xfailed", "xpassed")
    )
    assert collected, f"{target}: collected NOTHING\n{out[-3000:]}"
    red = counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
    keyerrors = sum(
        1
        for where, lineno, message in TB_LINE.findall(out)
        if DELITEM.search(f"{Path(where).name}:{lineno}: {message}")
    )
    return counts, red, keyerrors


def main() -> int:
    targets = sys.argv[1:]
    assert targets, "name at least one test module -- a nodeless pytest call " \
                    "collects the whole suite"
    SCRATCH.mkdir(parents=True, exist_ok=True)
    e1 = tree("e1-declarations-dropped", drop=True, assemble=False)
    e2 = tree("e2-dropped-and-assembled", drop=True, assemble=True)

    print(f"{'module':52} {'E0':>14} {'E1 drop':>14} {'E2 drop+asm':>14} "
          f"{'probe':>14}")
    for target in targets:
        row = []
        for label, src, probe in (
            ("E0", None, None),
            ("E1", e1, None),
            ("E2", e2, None),
            ("probe", None, "probe_five_kinds"),
        ):
            counts, red, keyerrors = run(target, src=src, probe=probe)
            row.append((label, red, keyerrors, counts.get("passed", 0)))
        cells = "  ".join(
            f"{label}:{red:>4}(KE {keyerrors:>2})" for label, red, keyerrors, _p in row
        )
        print(f"{target:52} {cells}")
        by = dict((label, red) for label, red, _k, _p in row)
        ke = dict((label, keyerrors) for label, _r, keyerrors, _p in row)
        print(f"    delitem KeyErrors — E1 {ke['E1']}, E2 {ke['E2']}, "
              f"probe {ke['probe']}: if E1/E2 carry them too, they are the "
              f"CONVERSION's residue, not the probe's shadow")
        print(f"    the writer rebinding alone moves {by['E2'] - by['E1']:+d} reds "
              f"(E2 - E1); probe vs E2 differ by {by['probe'] - by['E2']:+d}, "
              f"which is the probe's fidelity to the end state it simulates")
    shutil.rmtree(e1, ignore_errors=True)
    shutil.rmtree(e2, ignore_errors=True)
    sweep(ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
