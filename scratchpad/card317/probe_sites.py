"""Resolve the refs declared at given sites, both ways. CARD-317's probe.

Refs are named by their DECLARATION SITE (``requirements.yml:288``,
``adr/0006-dependency-baseline.md:57``, ``trace.yml:412``) and never spelled
here, for the reason in ``census_dump.py``'s docstring: ``scratchpad/`` is in
the validator's loose-resolution domain, so writing a ref name in this file
would resolve it and move the classes the round is measuring.

Usage::

    python scratchpad/card317/probe_sites.py <site-substring> [<site-substring>...]

A site argument matches a ``Declared.sources`` entry by substring, so
``requirements.yml:288`` matches ``requirements.yml:288 (test:)``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests import test_check_ref_resolution as guard  # noqa: E402


def main() -> int:
    wanted = sys.argv[1:]
    if not wanted:
        print(__doc__)
        return 2
    hit = 0
    for verdict in guard._verdicts():
        if not any(
            any(site in source for source in verdict.declared.sources) for site in wanted
        ):
            continue
        hit += 1
        klass = (
            "falsely-alive"
            if verdict.falsely_alive
            else "falsely-dead"
            if verdict.falsely_dead
            else "honest-dead"
            if not verdict.loose and not verdict.strict
            else "defined+alive"
        )
        print(
            f"{verdict.ref}\n"
            f"    class       : {klass}"
            f"{' (bookkeeping-only)' if verdict.bookkeeping_only else ''}\n"
            f"    form        : {verdict.declared.form}\n"
            f"    declared by : {', '.join(verdict.declared.sources)}\n"
            f"    resolved by : {', '.join(verdict.loose) or '(nothing)'}\n"
            f"    defined at  : {', '.join(verdict.strict) or '(nowhere)'}"
        )
    if not hit:
        raise SystemExit(f"no declared ref matched any of {wanted} -- an empty probe is not a pass")
    print(f"\n{hit} ref(s) matched {len(wanted)} site(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
