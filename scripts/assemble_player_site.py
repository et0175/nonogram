#!/usr/bin/env python3
"""Assemble the public player's deployable site, end to end (CARD-285, item 1).

    ./.venv/bin/python scripts/assemble_player_site.py \
        --bundle build/player-bundle --out build/site --analytics

**This is a driver and not an assembler.** Every byte of the output tree is
written by ``player/assemble.py`` — the player pages, the exported bundle's
rebuilt JSON, the byte-identical ``solver_state.js`` and ``tokens.css`` copies
from the panel, ``vercel.json`` and the ``.player-site`` marker. Nothing here
copies a file, and nothing here knows the published paths. That is deliberate:
``COPIED_FROM_ADMIN``'s equality is checked at assembly time *and* from the
test tree precisely so the two copies cannot drift, and a second assembler
would be a second place for them to drift in.

What this script adds to the assembler is exactly one thing the assembler must
not have: it reads the **analytics endpoints out of
``docs/deploy/player.md``** and passes them on the command line. Those two
values are owner-managed — a GoatCounter site code the owner registers — and
AC-392 makes that page the allow-list a scan of the assembled site is held to.
So the page is the configuration, read by this script at assembly time and by
``tests/test_public_player_pages.py::test_no_homegrown_tracking`` at scan time,
and the site cannot reference an endpoint the page does not name without one of
the two reding. ``player/assemble.py`` stays standard-library-only and knows
nothing about ``docs/`` (ADR-0041/R3, ADR-0006/R1 untouched).

Which is also why the parsing lives here rather than there, and the split is
worth one sentence: the assembler is the deployable artefact's producer and has
to run against a bare ``player/`` directory; this driver is a repository
convenience and may read the repository.

**Counting is opt-IN: ``--analytics``.** A bare run assembles the tree with no
snippet at all, which is what a local run and every test fixture want, so
development traffic cannot reach the owner's numbers. Cycle 2 of this card's
review measured the opposite default here and was right to call it a defect:
``docs/deploy/player.md``'s drift rule is "do not count locally", and a rule
whose safe side needs a remembered flag is not a rule — which is the same
argument this card makes about a control that cannot fail (ADR-0039/R2). The
deploy step is the explicit one now, and it is explicit in the page's own
command. ``--print-only`` prints the delegated command line and stops, for a
reader who wants to see what was driven without writing anything.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The page that holds the endpoints, and the fenced block in it that is the
#: allow-list. Both named here once: this script, the deploy page and the
#: AC-392 scanner all have to agree on where the value lives, and the scanner
#: imports these names from this module rather than restating them.
DEPLOY_DOC = Path("docs/deploy/player.md")

#: ``(sentinel, what it holds)``. ``RUNTIME_BLOCK``'s endpoints are the ones a
#: visitor's browser fetches and the ones injected into the pages;
#: ``STATIC_BLOCK``'s are references nothing fetches at page load (today the
#: ``vercel.json`` ``$schema``), named so a scan can classify them instead of
#: reporting them as unknown — an unclassifiable reference is a failure, so
#: "declared and harmless" has to be a thing the page can say.
RUNTIME_BLOCK = "analytics-allow-list"
STATIC_BLOCK = "non-runtime-allow-list"

#: The block the QR URL base and the three URL shapes live in (card item 4).
#: CARD-210 consumes it; it is parsed here so that "the doc says it" and "the
#: tooling reads it" are the same statement.
QR_BLOCK = "qr-url-shapes"

#: The endpoint names :func:`allow_list` must find in :data:`RUNTIME_BLOCK`.
#: A closed set: a page that stopped naming one of them would otherwise
#: assemble an uncounted or half-counted site.
REQUIRED_RUNTIME = ("count", "script")


def _block(text: str, sentinel: str) -> str:
    """The body between ``<!-- BEGIN sentinel -->`` and its ``END``.

    Missing, duplicated or inverted sentinels are a :class:`ValueError`. The
    page is configuration, and a configuration file this script cannot read
    unambiguously is one it must not guess at.
    """
    begin, end = f"<!-- BEGIN {sentinel} -->", f"<!-- END {sentinel} -->"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(
            f"{DEPLOY_DOC} must hold exactly one {begin} and one {end}; found "
            f"{text.count(begin)} and {text.count(end)}"
        )
    body = text.split(begin, 1)[1].split(end, 1)
    if len(body) != 2:
        raise ValueError(f"{DEPLOY_DOC}'s {end} comes before its {begin}")
    return body[0]


#: ``name = value`` inside a block, ignoring the fence lines and blanks.
_SETTING = re.compile(r"^\s*([a-z_][a-z0-9_]*)\s*=\s*(\S.*?)\s*$")


def _settings(body: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in body.splitlines():
        if not line.strip() or line.lstrip().startswith("```"):
            continue
        match = _SETTING.match(line)
        if match is None:
            raise ValueError(f"{DEPLOY_DOC}: {line!r} is not a `name = value` line")
        name, value = match.group(1), match.group(2)
        if name in found:
            raise ValueError(f"{DEPLOY_DOC}: {name} is set twice")
        found[name] = value
    if not found:
        raise ValueError(f"{DEPLOY_DOC}: a declared block is empty")
    return found


def allow_list(root: Path = REPO_ROOT) -> tuple[dict[str, str], dict[str, str]]:
    """``(runtime, non-runtime)`` endpoints, read from :data:`DEPLOY_DOC`.

    The authority AC-392's scan is derived from (ADR-0039/R2): the set comes
    out of a page a human maintains on purpose, not out of a literal in a
    test. Every value must be an absolute ``https`` URL, because that is the
    only shape either reader can compare against what a browser would fetch.
    """
    text = (root / DEPLOY_DOC).read_text(encoding="utf-8")
    runtime = _settings(_block(text, RUNTIME_BLOCK))
    static = _settings(_block(text, STATIC_BLOCK))
    missing = [name for name in REQUIRED_RUNTIME if name not in runtime]
    if missing:
        raise ValueError(
            f"{DEPLOY_DOC}'s {RUNTIME_BLOCK} does not name {', '.join(missing)}"
        )
    for where, block in ((RUNTIME_BLOCK, runtime), (STATIC_BLOCK, static)):
        for name, value in block.items():
            if not value.startswith("https://"):
                raise ValueError(
                    f"{DEPLOY_DOC}'s {where} entry {name} is not an https URL: {value!r}"
                )
    return runtime, static


def qr_shapes(root: Path = REPO_ROOT) -> dict[str, str]:
    """The QR URL base and the three URL shapes, read from :data:`DEPLOY_DOC`.

    ``base`` is a single owner-managed value and the rest are ``{base}``-
    relative templates, so CARD-210 reads one dictionary rather than
    reconstructing paths from ``vercel.json`` itself.
    """
    text = (root / DEPLOY_DOC).read_text(encoding="utf-8")
    return _settings(_block(text, QR_BLOCK))


def assembler(root: Path = REPO_ROOT):
    """``player/assemble.py``, loaded by path.

    ``player/`` is not a package and is not on ``sys.path`` — ADR-0041/R3 puts
    the public player outside the Python package, and putting it on the path to
    drive it would undo that. Same loading as the test tree's.
    """
    path = root / "player" / "assemble.py"
    spec = importlib.util.spec_from_file_location("player_assemble", path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable
        raise RuntimeError(f"cannot load the assembler from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def delegated_argv(
    *,
    bundle: str | None,
    out: str,
    force: bool,
    analytics: tuple[str, str] | None,
) -> list[str]:
    """The ``player/assemble.py`` command line this script would run.

    Separate from :func:`main` so that ``--print-only`` prints the same list
    that runs, and so a test can read the driver's whole contribution without
    assembling anything.
    """
    argv = ["--out", out]
    if bundle is not None:
        argv += ["--bundle", bundle]
    if force:
        argv.append("--force")
    if analytics is not None:
        argv += ["--analytics-count", analytics[0], "--analytics-script", analytics[1]]
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--bundle",
        default="build/player-bundle",
        help="the exported player bundle directory (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default="build/site",
        help="where to write the site; it IS the deployable tree (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="erase --out even when no previous run wrote it",
    )
    parser.add_argument(
        "--analytics",
        action="store_true",
        help=(
            "inject the counting snippet, with the endpoints read from "
            f"{DEPLOY_DOC} (the deploy does this; a local run must not)"
        ),
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="print the delegated player/assemble.py command line and stop",
    )
    args = parser.parse_args(argv)

    # Opt-in, so the default is the uncounted tree and "do not count
    # locally" is the shape of the command rather than something to
    # remember.
    analytics: tuple[str, str] | None = None
    if args.analytics:
        runtime, _ = allow_list()
        analytics = (runtime["count"], runtime["script"])

    delegated = delegated_argv(
        bundle=args.bundle, out=args.out, force=args.force, analytics=analytics
    )
    print(f"driving player/assemble.py {' '.join(delegated)}")
    if analytics is None:
        print(f"  no counting snippet (no --analytics); {DEPLOY_DOC} not read")
    else:
        print(f"  counting endpoints from {DEPLOY_DOC}: {analytics[0]}")
    if args.print_only:
        return 0
    return int(assembler().main(delegated))


if __name__ == "__main__":  # pragma: no cover - the command line
    sys.exit(main())
