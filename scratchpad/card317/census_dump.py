"""Dump the six frozen ref classes of tests/test_check_ref_resolution.py.

CARD-317's instrument. It spells **no** ref name of its own: every name it
prints is derived at run time by importing the guard module and calling its own
derivation. That is not a style preference -- ``scratchpad/`` is inside the
validator's loose-resolution domain (``_in_domain_files`` excludes only
``meta/architecture/`` and ``*.md``), so a ref name written literally here
would be *resolved* by the validator's text search and would move the very
classes this file exists to measure.

Usage::

    python scratchpad/card317/census_dump.py <out-dir-OUTSIDE-the-repo>

Writes one file per class, one ref per line, sorted, plus ``counts.txt``
carrying each class's (count, fingerprint) exactly as the baselines store it.
The output must live outside the repo for the same reason as above.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tests import test_check_ref_resolution as guard  # noqa: E402


def classes() -> dict[str, tuple[str, ...]]:
    verdicts = guard._verdicts()
    trace = tuple(
        sorted(
            d.ref
            for d in guard._declared_refs()
            if any(s.startswith("trace.yml:") for s in d.sources)
        )
    )
    return {
        "bookkeeping_only": tuple(sorted(v.ref for v in verdicts if v.bookkeeping_only)),
        "falsely_alive": tuple(sorted(v.ref for v in verdicts if v.falsely_alive)),
        "defined": tuple(sorted(v.ref for v in verdicts if v.strict)),
        "honest_dead": tuple(
            sorted(v.ref for v in verdicts if not v.loose and not v.strict)
        ),
        "census": tuple(sorted(d.ref for d in guard._declared_refs())),
        "trace_tests": trace,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1])
    if out.is_relative_to(REPO_ROOT):
        raise SystemExit(f"{out} is inside the repo; dumps must not be tracked")
    out.mkdir(parents=True, exist_ok=True)
    counts = []
    for name, refs in classes().items():
        (out / f"{name}.txt").write_text("\n".join(refs) + "\n", encoding="utf-8")
        # The baselines fingerprint the class in its own order; _fingerprint
        # sorts internally, so the tuple order here is immaterial.
        counts.append(f"{name} = ({len(refs)}, {guard._fingerprint(refs)!r})")
    (out / "counts.txt").write_text("\n".join(counts) + "\n", encoding="utf-8")
    print("\n".join(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
