#!/usr/bin/env python3
"""Serve an assembled player site locally, with vercel.json's rewrites applied.

    ./.venv/bin/python scripts/preview_player_site.py            # build/site on 8081
    ./.venv/bin/python scripts/preview_player_site.py build/site 8081

**Why this exists rather than `python -m http.server`.** Two of the site's three
doors are rewrites, not files: `/play/<key>` and `/b/<slug>` are served by one
document each (`play/index.html`, `b/index.html`) and the key or slug is read out
of the path by the page's own script. A plain static server looks for a file of
that literal name and answers 404, which reads as a broken tree when the tree is
fine — measured 2026-10-29, on a site that then deployed correctly. `/library`
happens to work there by directory index, so the failure is partial, which is
worse.

The rewrite table is read from the SERVED tree's own ``vercel.json`` — the same
file the host routes by, and the same file
``tests/test_public_player_pages.py`` derives its routing fixtures from — so this
preview cannot drift from what deploys. A source added to that file is served here
without touching this script.

**What this is not.** It is not Vercel's router and not a deploy rehearsal: no
cache headers, no `cleanUrls`, no trailing-slash handling, and nothing about the
counting snippet (a locally assembled tree carries none by default — see
``docs/deploy/player.md``'s "do not count locally"). It answers one question —
do the pages render and play — and that is all it is for.

Standard library only, like ``player/assemble.py`` and for the same reason
(ADR-0006/R1 untouched): a preview of a no-toolchain site should need no
toolchain either.
"""

from __future__ import annotations

import json
import re
import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

#: Where the assembler writes by default, and the port this serves on.
DEFAULT_ROOT = "build/site"
DEFAULT_PORT = 8081

#: The marker ``player/assemble.py`` writes into every tree it builds. A
#: directory without it is not an assembled site, and serving one would answer
#: the question with somebody else's files.
SITE_MARKER_FILE = ".player-site"


def rewrites(root: Path) -> list[tuple[re.Pattern[str], str]]:
    """``vercel.json``'s rules as ``(pattern, destination)``, in file order.

    A ``:name`` segment in a source becomes "one path segment, no slash" — which
    is what the host matches — and a trailing slash is tolerated so ``/library/``
    lands on the same document as ``/library``.
    """
    config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))
    rules = []
    for rule in config["rewrites"]:
        pattern = "^" + re.sub(r":(\w+)", r"[^/]+", rule["source"]) + "/?$"
        rules.append((re.compile(pattern), rule["destination"]))
    return rules


class RewritingHandler(SimpleHTTPRequestHandler):
    """``SimpleHTTPRequestHandler`` that consults the rewrite table first."""

    rules: list[tuple[re.Pattern[str], str]] = []

    def _rewrite(self) -> None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        for pattern, destination in self.rules:
            if pattern.match(path):
                self.path = destination
                return

    def do_GET(self) -> None:  # noqa: N802 - the base class's spelling
        self._rewrite()
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - the base class's spelling
        self._rewrite()
        super().do_HEAD()


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else DEFAULT_ROOT)
    port = int(argv[2]) if len(argv) > 2 else DEFAULT_PORT

    if not (root / SITE_MARKER_FILE).is_file():
        print(
            f"{root} holds no {SITE_MARKER_FILE} marker, so no run of "
            f"player/assemble.py wrote it. Assemble a site first:\n"
            f"    ./.venv/bin/python scripts/assemble_player_site.py "
            f"--bundle build/player-bundle --out {root}",
            file=sys.stderr,
        )
        return 2

    RewritingHandler.rules = rewrites(root)
    print(f"serving {root} on http://localhost:{port}")
    for pattern, destination in RewritingHandler.rules:
        print(f"  {pattern.pattern}  ->  {destination}")
    HTTPServer(("127.0.0.1", port), partial(RewritingHandler, directory=str(root))).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
