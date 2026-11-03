"""CARD-338 AC-1: the probe cannot silently measure nothing — **proved** by
running it against trees it must refuse.

Not a test and not under ``tests/`` (G-2). Run from the worktree root::

    python scratchpad/card338/prove_refusals.py

AC-1 is the card: a probe that rebinds a global that has been renamed, or lifts
a kind already absent, must fail with a message naming what it could not do,
and must never run the session green over a tree it did not change. An
assertion nobody has seen fire is a claim, so this script **stands each failure
up** and checks the refusal.

**How a mutated tree is made without touching ``src/`` (G-1).** ``src/`` is
copied into a scratch directory, the copy is mutated, and pytest is run with
``-o pythonpath=<copy>`` — which pytest inserts at ``sys.path[0]``, ahead of
the editable install's ``.pth`` entry for the real tree. Every case asserts
that the module actually imported came **from the copy** before trusting its
verdict, because a refusal proved against the unmutated tree would prove
nothing.

The cases, each a way this instrument could go quiet:

1-5. one of the five declarations is already absent (the tree is partly
     converted: CARD-322 has landed that kind);
6.   the writer-rebinding target is renamed, so the generator's default writer
     set cannot be found by name;
7.   the assembly point's writer set is partial, so the kinds it does not
     cover would be refused rather than drawn;
8.   the constructor stops reading the module global, so rebinding it is a
     **no-op** — the quietest failure of all, and the one a ``hasattr`` check
     alone would miss;
9.   the control: the unmutated tree, which must be accepted. Without it the
     eight refusals above would also be satisfied by a probe that refuses
     everything.
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
#: One cheap, file-scoped target. The refusal happens in ``pytest_configure``,
#: before collection, so the target only has to exist — but a nodeless pytest
#: call collects the whole suite, so one is always passed.
TARGET = "tests/test_book_interior_face.py"
GENERATOR = "src/nonogram/admin/book_pdf_generator.py"
ASSEMBLY = "src/nonogram/admin/book_interior_vector.py"


def sweep(where: Path) -> None:
    for cache in where.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def fresh_copy(name: str) -> Path:
    """``src/`` copied to a scratch directory, ready to be mutated."""
    into = SCRATCH / "trees" / name
    if into.exists():
        shutil.rmtree(into)
    into.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "src", into / "src")
    sweep(into)
    return into


def drop_declaration(tree: Path, kind: str) -> None:
    """Make the copy a tree where ``kind`` is already converted."""
    path = tree / GENERATOR
    path.write_text(
        path.read_text()
        + f"\n\n# CARD-338 prove_refusals: {kind} is already converted here.\n"
        f"_RASTER_DECLARATIONS.pop(PageKind.{kind}, None)\n"
    )


def rename_target(tree: Path) -> None:
    """Rename the global the probe rebinds.

    A rename touches every occurrence by design, so the pin here cannot be
    ``count == 1`` on the name. It is ``count == 1`` on each of the two sites
    that make the case mean anything -- the definition and the constructor's
    read -- plus "nothing is left behind": a plant that silently matched a
    docstring and not the code would otherwise score as a proof.
    """
    path = tree / GENERATOR
    source = path.read_text()
    for phrase in (
        "NO_DOWNSTREAM_WRITERS = InteriorPageWriters()",
        "self.pages = NO_DOWNSTREAM_WRITERS if pages is None else pages",
    ):
        assert source.count(phrase) == 1, (
            f"{GENERATOR}: expected EXACTLY ONE `{phrase}`, found "
            f"{source.count(phrase)} -- re-read the module before trusting "
            "this case"
        )
    renamed = source.replace("NO_DOWNSTREAM_WRITERS", "NO_WRITERS_AT_ALL")
    assert "NO_DOWNSTREAM_WRITERS" not in renamed, (
        f"{GENERATOR}: the rename left the old name behind, so the probe could "
        "still find its target and this case would prove nothing"
    )
    path.write_text(renamed)


def partial_writers(tree: Path) -> None:
    """Shadow the assembly point's writer set with a partial one.

    Pinned the same way: the name this append re-binds must be defined
    exactly once above, or the "partial set" is a new name nothing reads.
    """
    path = tree / ASSEMBLY
    source = path.read_text()
    assert source.count("DOWNSTREAM_WRITERS = ") == 1, (
        f"{ASSEMBLY}: expected EXACTLY ONE `DOWNSTREAM_WRITERS = ` to shadow, "
        f"found {source.count('DOWNSTREAM_WRITERS = ')} -- re-read the module "
        "before trusting this case"
    )
    path.write_text(
        source
        + "\n\n# CARD-338 prove_refusals: the assembly point lost a writer.\n"
        "DOWNSTREAM_WRITERS = InteriorPageWriters(\n"
        "    guide=None,\n"
        "    toc=toc_page_stream,\n"
        "    answer=answer_page,\n"
        "    packed_answer=packed_answer_page,\n"
        ")\n"
    )


def stop_reading_the_global(tree: Path) -> None:
    """The constructor no longer reads the module global, so rebinding it does
    nothing at all and a ``hasattr`` check would still pass."""
    path = tree / GENERATOR
    source = path.read_text()
    old = "self.pages = NO_DOWNSTREAM_WRITERS if pages is None else pages"
    assert source.count(old) == 1, (
        f"{GENERATOR}: expected EXACTLY ONE constructor line this case mutates "
        f"(`{old}`), found {source.count(old)} -- `str.replace` would plant in "
        "all of them and the case would no longer be the one named"
    )
    path.write_text(
        source.replace(old, "self.pages = InteriorPageWriters() if pages is None else pages")
    )


CASES = [
    (f"declaration {kind} already absent", lambda t, k=kind: drop_declaration(t, k), True)
    for kind in ("PUZZLE", "TITLE", "GUIDE", "TOC", "ANSWER")
] + [
    ("writer-rebinding target renamed", rename_target, True),
    ("assembly point's writer set is partial", partial_writers, True),
    ("constructor stops reading the global (rebinding is a no-op)",
     stop_reading_the_global, True),
    ("CONTROL: the unmutated tree", lambda tree: None, False),
]

IMPORTED_FROM = re.compile(r"^CARD338-IMPORTED-FROM (.*)$", re.M)

#: The repository conftest's own refusal when a SIBLING WORKTREE holds the
#: full-suite lock. Added CARD-338 fix round 2, and measured against a real
#: held lock (CARD-323's merge gate) rather than a simulated one.
#:
#: Without this, every ``pytest`` call below exits non-zero carrying this text
#: and none of our assertion phrases, so all eight refusal cases score FAIL for
#: an empty ``named`` list, the CONTROL scores FAIL for refusing, and the script
#: prints "AC-1 NOT PROVED: 9 of 9 cases wrong". That is a refusal of the
#: ENVIRONMENT reported as a verdict about the INSTRUMENT -- the exact confusion
#: this card exists to close, in this card's own tooling. "Could not measure" is
#: not "measured and wrong", and AC-1's own standard is that a refusal must name
#: what it could not do.
LOCK_REFUSAL = "another worktree holds the full-suite lock"


def assertion_surface(out: str) -> str:
    """The lines a refusal's own message can be on, and no others.

    Every line carrying ``AssertionError`` plus the two after it, because an
    assertion message long enough to wrap continues on them. Searching the
    whole of stdout+stderr instead is how a case gets scored "named" on an
    unrelated line.
    """
    lines = out.splitlines()
    keep: set[int] = set()
    for index, line in enumerate(lines):
        if "AssertionError" in line:
            keep.update(range(index, min(index + 3, len(lines))))
    return "\n".join(lines[index] for index in sorted(keep))


def run(tree: Path) -> tuple[int, str]:
    sweep(ROOT)
    env = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=f"{HERE}{os.pathsep}{SCRATCH}",
    )
    done = subprocess.run(
        [
            str(PYTHON), "-m", "pytest",
            "-o", "addopts=",
            "-o", f"pythonpath={tree / 'src'}",
            "-q", "-rfs", "--tb=short", "--collect-only",
            "-p", "probe_five_kinds",
            "-p", "where_from",
            TARGET,
        ],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
    )
    sweep(ROOT)
    sweep(tree)
    return done.returncode, done.stdout + done.stderr


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # A one-line plugin that reports which tree was actually imported, so a
    # case cannot be "proved" against the unmutated source. It is written into
    # the SESSION scratchpad, not beside this file: G-3 keeps the card's own
    # scratchpad to committed instruments only.
    (SCRATCH / "where_from.py").write_text(
        '"""CARD-338: report which tree the generator was imported from.\n\n'
        "Loaded with ``-p`` BEFORE ``probe_five_kinds`` in\n"
        "``prove_refusals.py``, so the line below is printed even when the\n"
        "probe then refuses. A refusal proved against the unmutated tree\n"
        'proves nothing, and this is what makes that checkable."""\n\n'
        "from nonogram.admin import book_pdf_generator as _generator\n\n"
        'print("CARD338-IMPORTED-FROM " + _generator.__file__)\n'
    )

    failures = []
    for name, mutate, must_refuse in CASES:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        tree = fresh_copy(slug)
        mutate(tree)
        code, out = run(tree)
        if LOCK_REFUSAL in out:
            # Stop at the FIRST case: the remaining eight would each repeat this
            # one environmental cause, and a list of nine identical FAILs reads
            # as nine findings.
            shutil.rmtree(tree, ignore_errors=True)
            (SCRATCH / "where_from.py").unlink(missing_ok=True)
            sweep(ROOT)
            print()
            print("COULD NOT MEASURE -- this is not a result about the probe.")
            print(f"  pytest refused to start at case {name!r}:")
            print(f"  {LOCK_REFUSAL}.")
            for line in out.splitlines():
                stripped = line.strip()
                if stripped.startswith(("holder:", "why:", "worktree:", "at:",
                                        "age:", "lock:")):
                    print(f"    {stripped}")
            print("  Every case would score FAIL for this one cause and the")
            print("  summary would read 'AC-1 NOT PROVED', which would be a")
            print("  FALSE NEGATIVE. Nothing has been proved or disproved.")
            print("  Wait for the lock file to disappear and re-run.")
            return 3
        where = IMPORTED_FROM.search(out)
        imported = where.group(1) if where else "<not reported>"
        from_copy = imported.startswith(str(tree))
        refused = code != 0
        # The refusal must NAME what it could not do: an AssertionError with no
        # message would satisfy "non-zero exit" and teach a reader nothing.
        #
        # Scoped to the ASSERTION SURFACE, not to the whole of stdout+stderr: a
        # phrase found on an unrelated line would score the case "named" while
        # the assertion itself said nothing. Each phrase below is a literal
        # slice of one of probe_five_kinds.py's own assertion messages -- the
        # bare "declares" this list used to carry matched almost any English
        # sentence pytest could print.
        surface = assertion_surface(out)
        named = [
            phrase
            for phrase in (
                "found no", "cannot rebind", "cannot read", "has no writer for",
                "does not hold the rebound", "measures nothing",
                "in expires_with and the census is",
                "the registry declares",
            )
            if phrase in surface
        ]
        ok = (
            from_copy
            and refused == must_refuse
            and (bool(named) if must_refuse else True)
        )
        verdict = "OK  " if ok else "FAIL"
        print(f"{verdict} [{'refuse' if must_refuse else 'accept'}] {name}")
        print(f"       imported from the copy: {from_copy}  ({imported})")
        print(f"       exit {code}, refused={refused}")
        if must_refuse:
            quoted = [
                line.strip()
                for line in surface.splitlines()
                if "AssertionError" in line or "measures nothing" in line
            ]
            for line in quoted[:3]:
                print(f"       message: {line[:200]}")
            print(f"       phrases naming what it could not do: {named}")
        if not ok:
            failures.append((name, code, out[-4000:]))
        shutil.rmtree(tree, ignore_errors=True)

    (SCRATCH / "where_from.py").unlink(missing_ok=True)
    sweep(ROOT)
    print()
    if failures:
        for name, code, out in failures:
            print(f"\n########## FAILED CASE: {name} (exit {code})\n{out}")
        print(f"AC-1 NOT PROVED: {len(failures)} of {len(CASES)} cases wrong")
        return 1
    print(f"AC-1 PROVED: {len(CASES)} cases, 8 refusals named and 1 control accepted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
