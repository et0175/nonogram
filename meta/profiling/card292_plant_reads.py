"""CARD-292 AC-1's second instrument: what ``_plant``'s disk reads actually
cost, measured instead of narrated.

The card carries a MECHANISM STORY for the ~120 s boundary -- *"inside a suite
the module's 306 KB source is in the page cache by the time this file runs, and
standalone it is not; ``_plant`` reads it from disk 144 times in that one
test"* -- and AC-1 requires that story confirmed or refuted by timing those
reads rather than by repeating it.  This script times them.

It does NOT run under pytest: it imports the test module by path and calls the
one test's body directly, with ``Path.read_text`` wrapped by a counter.  That
keeps it out of ``tests/`` (G-3) and out of any suite collection.

Run::

    python meta/profiling/card292_plant_reads.py

Reported, per the card's "name the door you derived it through":

* how many times ``Path.read_text`` is called during the test, and on which
  paths -- the card's "144" is a figure to recompute, not to quote;
* how much was read, in CHARACTERS -- this counts ``len(text)`` AFTER
  ``read_text`` has decoded, so its domain is characters and not bytes, and
  the two differ here because the module is not all-ASCII (CARD-292 review
  cycle 1, F-004: 389,177 characters against 390,485 bytes on disk);
* the seconds spent inside ``read_text``, split into the FIRST read of each
  distinct path and all later reads of it.  That split is the whole argument:
  the first read is the only one that can be cold, because it populates the
  page cache itself, so a page-cache story has exactly ONE READ PER DISTINCT
  PATH to pay for -- two, as this test reads two modules.
* the test's own wall clock, so the read share is a share and not a number.
"""

import importlib.util
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
TEST_FILE = REPO / "tests" / "test_book_export_interior_cover.py"
TEST_NAME = "test_each_door_axis_arm_catches_a_shape_the_other_misses"
CLASS_NAME = "TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage"


def _load():
    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO))
    spec = importlib.util.spec_from_file_location("card292_subject", TEST_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["card292_subject"] = module
    spec.loader.exec_module(module)
    return module


def main():
    module = _load()
    cls = getattr(module, CLASS_NAME)

    reads = []  # (path, seconds, nchars)
    real = pathlib.Path.read_text

    def counting(self, *a, **kw):
        started = time.perf_counter()
        text = real(self, *a, **kw)
        reads.append((str(self), time.perf_counter() - started, len(text)))
        return text

    pathlib.Path.read_text = counting
    try:
        started = time.perf_counter()
        getattr(cls(), TEST_NAME)()
        wall = time.perf_counter() - started
    finally:
        pathlib.Path.read_text = real

    seen = set()
    first_s = later_s = 0.0
    first_n = later_n = 0
    for path, seconds, nchars in reads:
        if path in seen:
            later_s += seconds
            later_n += 1
        else:
            seen.add(path)
            first_s += seconds
            first_n += 1

    total_s = first_s + later_s
    total_chars = sum(n for _, _, n in reads)
    print(f"test              {CLASS_NAME}::{TEST_NAME}")
    print(f"test wall clock   {wall:.2f} s")
    print(f"read_text calls   {len(reads)}")
    print(f"distinct paths    {len(seen)}")
    for path in sorted(seen):
        n = sum(1 for p, _, _ in reads if p == path)
        print(f"  {n:4d} x  {path}")
    print(
        f"characters read   {total_chars} ({total_chars / 1e6:.1f} M chars; "
        "len(text) AFTER decode, so the unit is characters, not bytes)"
    )
    print(f"seconds in reads  {total_s:.4f} s  = {100 * total_s / wall:.3f}% of the test")
    print(f"  first read of each path  {first_n} reads, {first_s:.4f} s")
    print(f"  every later read         {later_n} reads, {later_s:.4f} s")
    print(
        "COLD-CACHE CEILING: a page-cache story can only charge for the "
        f"{first_n} first read(s); the other {later_n} are warm BY CONSTRUCTION, "
        "because the first read populates the cache."
    )


if __name__ == "__main__":
    main()
