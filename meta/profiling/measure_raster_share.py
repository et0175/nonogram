"""How much suite time do the interior-raster assertions actually hold?

The owner's question: can we stop running the tests that measure raster? The
cost half of that needs a number nobody has — ADR-0042's census counted 315
pixel-reading SITES across 32 files, but a site count is not a time share.

Joined from two existing measurements so nothing has to be run (a fresh profile
would hold the board's full-suite lock for ~26 min and red the live CARD-296
agent's every pytest run):

  * meta/profiling/suite-durations-20261023.txt — 26,917 phase records from a
    solo, lock-held run at ae164099, format-matched to the 2026-10-15 baseline.
  * meta/profiling/adr-0042-migration-census.md — the 32 files and their site
    counts.

STALENESS, stated rather than hidden: the profile predates CARD-276 (+37 tests)
and CARD-294 (+67), so it is ~104 tests light against today's 9,254 and does
not include CARD-294's two new files. Shares are therefore order-of-magnitude
honest and the second decimal is not.
"""

import pathlib
import re
import sys
from collections import defaultdict

def main() -> int:
    """The whole measurement, in a function.

    Module scope holds nothing that can stop this file being collected.
    `tests/test_guard_integrity.py::TestGuardModule_CannotGoQuietAboveItsOwnGuards`
    walks `meta/profiling/` as well as `tests/`, and a module-scope `exit()`
    under a condition takes every guard in the file with it and reads as a
    skip rather than as a failure. This script had exactly that shape when it
    was committed (431f00c2) and it broke `main` until CARD-283's merge gate
    found it.
    """
    ROOT = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4")
    PROF = ROOT / "meta/profiling/suite-durations-20261023.txt"
    CENSUS = ROOT / "meta/profiling/adr-0042-migration-census.md"

    # --- the census's 32 files, parsed rather than retyped -----------------------
    rows = re.findall(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*`([^`]+)`", CENSUS.read_text(), re.M)
    census = {f: (int(px), int(refs)) for px, refs, f in rows}
    assert len(census) == 32, len(census)

    # --- the groups ADR-0042/R6 keeps raster, from the census's own section ------
    # Named here because converting them is "a card that broke something".
    STAYS_RASTER = {
        "tests/test_book_cover.py": "the cover is raster by ADR-0042/R2 — a photograph",
        "tests/test_export_image.py": "COMP-007's CLI/web surface, CON-019 byte-identical",
        "tests/test_layout_page_spec.py": "COMP-007's CLI/web surface, CON-019 byte-identical",
    }
    # Partially raster: dividers keep today's reading until CARD-231.
    PARTIAL = {
        "tests/test_book_pdf_levels.py": "divider assertions stay until CARD-231",
        "tests/test_book_interior_type_floor.py": "the `divider` face stays until CARD-231",
    }

    # --- per-file time from the profile -----------------------------------------
    # Lines look like: "<sec>s <phase> <nodeid>"; sum every phase per file.
    per_file = defaultdict(float)
    total = 0.0
    for line in PROF.read_text().splitlines():
        m = re.match(r"^([0-9.]+)s\s+(call|setup|teardown)\s+(\S+)", line)
        if not m:
            continue
        secs, _phase, node = float(m.group(1)), m.group(2), m.group(3)
        total += secs
        per_file[node.split("::", 1)[0]] += secs

    if total == 0:
        print("parsed no phase records — the profile's format changed")
        return 1

    def share(x):
        return f"{x / total * 100:5.2f}%"

    print(f"attributed suite time in the profile: {total:8.2f}s across {len(per_file)} files\n")

    conv, stay, part = [], [], []
    for f, (px, refs) in census.items():
        t = per_file.get(f, 0.0)
        if f in STAYS_RASTER:
            stay.append((t, f, px, STAYS_RASTER[f]))
        elif f in PARTIAL:
            part.append((t, f, px, PARTIAL[f]))
        else:
            conv.append((t, f, px))

    conv.sort(reverse=True); stay.sort(reverse=True); part.sort(reverse=True)

    print("=" * 78)
    print("CONVERTIBLE — interior pages, ADR-0042/R6 retires pixel reading for these")
    print("=" * 78)
    print(f"{'time':>9}  {'share':>6}  {'px':>4}  file")
    for t, f, px in conv:
        print(f"{t:8.2f}s  {share(t)}  {px:4d}  {f}")
    c_t, c_px = sum(t for t, _, _ in conv), sum(px for _, _, px in conv)
    print(f"{c_t:8.2f}s  {share(c_t)}  {c_px:4d}  ** {len(conv)} files **")

    print("\n" + "=" * 78)
    print("STAYS RASTER — converting these would break something")
    print("=" * 78)
    for t, f, px, why in stay + part:
        print(f"{t:8.2f}s  {share(t)}  {px:4d}  {f}\n{'':27}{why}")
    s_t = sum(t for t, _, _, _ in stay + part)
    print(f"{s_t:8.2f}s  {share(s_t)}  ** {len(stay) + len(part)} files **")

    print("\n" + "=" * 78)
    print("THE ANSWER")
    print("=" * 78)
    print(f"  census total              {c_t + s_t:8.2f}s  {share(c_t + s_t)} of attributed time")
    print(f"  of which CONVERTIBLE      {c_t:8.2f}s  {share(c_t)}")
    print(f"  of which MUST STAY RASTER {s_t:8.2f}s  {share(s_t)}")
    print()
    print("  the spike measured the stream assertion 4.1x smaller than the ink one")
    print("  it replaces (168 -> 41 lines) and strictly more exact. If conversion")
    print("  bought a proportional time saving on the convertible share alone:")
    for factor, label in ((4.1, "4.1x, the spike's line ratio"), (2.0, "2x, conservative")):
        saved = c_t - c_t / factor
        print(f"    at {label:28s} -> {saved:7.2f}s saved, {share(saved)} of the suite")
    print()
    print("  NOT a prediction: the spike's 4.1x is a LINE ratio, not a time ratio.")
    print("  The time claim it does support is per-page rendering (1.37 vs 11.7 ms,")
    print("  8.5x) and page-bitmap retention (1.00 -> 0.000246). A converted")
    print("  assertion stops rendering a page at all, so the saving is plausibly")
    print("  LARGER than these rows - but no one has measured a converted test's")
    print("  wall clock, and CARD-295/296/297 are the first chance to.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
