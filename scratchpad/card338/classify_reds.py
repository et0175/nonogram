"""CARD-338 AC-3: every red under the five-kind probe, grouped by **mechanism**
and attributed to an **owning card** — with no "other" bucket.

Not a test and not under ``tests/`` (G-2). Reads the census dump that
``census_five_kinds.py --causes`` writes, so the classification is a pure
function of a measurement and re-runs in seconds::

    python scratchpad/card338/census_five_kinds.py --third --causes > dump.txt
    python scratchpad/card338/classify_reds.py dump.txt

**AC-3 is that an unclassified group is a finding, not a bucket.** So this
script has no default group: a cause no rule below matches makes it exit
non-zero and print the cause verbatim. Adding a catch-all here would be the
defect the AC exists to prevent.

**Three ways a red could have escaped that guarantee, all closed.** (1) A red
printing under the ERRORS heading rather than as a ``--tb=line`` entry: the
census now parses those into the same ``x<n> [tag] <cause>`` shape
(``error_causes()``), so they reach the ``RULES`` table and the same non-zero
exit. (2) A dump line *shaped* like a cause line but not matching ``LINE``:
silently skipped before, now collected and reported as malformed with the same
non-zero exit. (3) Coverage asserted from the census's own figures rather than
from this walk: the classified total is cross-checked against the ``red=``
column of every module header, and a shortfall exits non-zero. Before these,
this script printed "no 'other' group" while blind to 23 of 233 reds (10%).

**The rules are ordered and the first match wins**, so a more specific
mechanism is written above a more general one. Each rule carries the card that
owns the repair, which is what a downstream card needs — a count without an
owner prices nothing.

The dump is **not committed** (G-3): the resolver is a ``git grep -lw`` text
search over tracked files excluding only ``meta/architecture`` and ``*.md``, so
a committed census spelling test names revives dead check refs (live on main
across ~245 files, carded as CARD-335). This file names no test; it names
message shapes.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

#: (pattern, mechanism, owner). First match wins. Filled from the measured
#: dump; every entry was read off a real cause line, never guessed.
RULES: list[tuple[str, str, str]] = [
    # ---------------------------------------------------------------- M1
    (
        r"monkeypatch\.py:\d+: KeyError: <PageKind\.",
        "M1 registry-popping site: a monkeypatch.delitem on _RASTER_DECLARATIONS "
        "reaching a key that is no longer there",
        "CARD-322 — NOT the probe's shadow: measured identical on a tree whose "
        "five entries are deleted in src/ with no probe loaded "
        "(fidelity_to_the_end_state.py)",
    ),
    # ---------------------------------------------------------------- M2
    (
        # The census prints a cause truncated to 160 characters, so this
        # pattern must match inside that window -- a rule anchored on the
        # tail of a long message silently matches nothing.
        r"no vector guide writer",
        "M2 expected-side gap: the vector arm has nothing to compare the shipped "
        "page against, and fails by name rather than passing",
        "CARD-322 — its message names CARD-309, which no longer owns it",
    ),
    # ---------------------------------------------------------------- M3
    (
        r"book_pdf_generator\.py:\d+: TypeError: page \d+ is a vector .* arrived as Image",
        "M3 production refusal reached: _write_pdf's own representation refusal, "
        "fired by a reader that re-rendered the page as a bitmap",
        "CARD-322",
    ),
    (
        r"book_pdf_generator\.py:\d+: RuntimeError: .*cp1252 encoding",
        "M3b production refusal newly REACHABLE: a glyph outside cp1252 only "
        "refuses once the page is drawn as operators, so the conversion makes "
        "this path live for the first time",
        "CARD-322 — raised as a finding: this is a product behaviour change, not "
        "a test repair",
    ),
    # ---------------------------------------------------------------- M4
    (
        r"the raster arm (of the difficulty-dot accounting )?is (DEAD|not alive)",
        "M4 CARD-331's raster arm declares itself dead on a vector puzzle page",
        "CARD-322 (item 2: re-point the arm and DERIVE RASTER_ARM_FUNCTIONS)",
    ),
    # ---------------------------------------------------------------- M5
    (
        r"(the registry no longer declares"
        r"|AssertionError: \['divider'\]"
        r"|AssertionError: \['answer', 'guide', 'puzzle', 'title', 'toc'\]"
        r"|test_book_pdf\.py:3224: AssertionError: 30"
        r"|test_book_pdf\.py:3745: AssertionError: \[\])",
        "M5 registry-derived guard: the cell's own expectation is computed from "
        "_RASTER_DECLARATIONS, so it moves when the registry shrinks",
        "CARD-322",
    ),
    # ---------------------------------------------------------------- M6
    (
        r"__init__\.py:\d+: KeyError: b'XObject'",
        "M6 reader seam, unprotected: an image XObject is read off a page that "
        "has none (PIL's own parser, through the one-image reader)",
        "CARD-337 (the nine routed modules' `interior_images` seam)",
    ),
    (
        r"PageMediumRefused",
        "M6b reader seam, protected: CARD-329's explicit refusal fires instead of "
        "a KeyError — the same mechanism with a message",
        "CARD-337",
    ),
    # ---------------------------------------------------------------- M7
    (
        r"page_ink\.py:\d+: AttributeError: 'ContentStream' object",
        "M7 pixel oracle handed a ContentStream: the shared ink oracle assumes a "
        "PIL image",
        "CARD-330 owns page_ink.py; the calling module's seam is CARD-337's "
        "(CARD-336's for the placed-edge callers)",
    ),
    (
        r"two_up_ink\.py:\d+: ValueError: the page carries no ink at all",
        "M7b two-up ink oracle on a vector page: same mechanism, its own helper",
        "CARD-337",
    ),
    (
        r"test_book_difficulty_dots\.py:\d+: AttributeError: 'ContentStream' object",
        "M7c pixel oracle handed a ContentStream, in CARD-331's own module",
        "CARD-331's arm, routed to CARD-322 by that card's item 2",
    ),
    (
        r"AttributeError: 'ContentStream' object has no attribute",
        "M7d pixel oracle handed a ContentStream, inside the test module itself",
        "CARD-337 (the module's own seam)",
    ),
    # ---------------------------------------------------------------- M8
    (
        r"test_book_pdf_geometry\.py:\d+: AssertionError: \(Sheet\("
        r"|test_book_pdf_geometry\.py:\d+: AssertionError: \(6, "
        r"|test_book_puzzle_frame\.py:\d+: (AssertionError: a row through the grid|assert )"
        r"|test_book_pdf_two_up\.py:\d+: assert 0\."
        r"|test_book_pdf_two_up\.py:\d+: AssertionError: \(0\.",
        "M8 placed-edge / geometry: a coordinate read off the page misses its "
        "bound by a measured multiple of HALF_PIXEL_MM",
        "CARD-336",
    ),
    # ---------------------------------------------------------------- M9
    (
        r"test_book_pdf_memory\.py:\d+: (AssertionError: assert \d+ == \d+"
        r"|AssertionError: interior page \d+ is not the page it was"
        r"|AssertionError: stored page \d+ is"
        r"|Failed: DID NOT RAISE)"
        r"|test_book_pdf_levels\.py:\d+: AssertionError: assert b'",
        "M9 byte identity: a page's stored or re-exported bytes are compared "
        "against a baseline recorded in the other medium",
        "CARD-337 (the byte-identity mechanism) / CARD-322 (item 5, the live "
        "baselines)",
    ),
    # ---------------------------------------------------------------- M10
    (
        r"(assert \[\]|AssertionError: \[\]|assert set\(\)"
        r"|AssertionError: assert \[\] =="
        r"|AssertionError: \(\[\], "
        r"|assert \d+ >= \d+|AssertionError: assert \d+ == \d+"
        r"|IndexError: (list index out of range|index 0 is out of bounds)"
        r"|assert False|AssertionError: assert False"
        r"|printed no |drew no text|no band was drawn|carried a name at all"
        r"|no answer captions to look for|set no caption"
        r"|only \d+ pages carried a measurable drawing"
        r"|no \d+-row puzzle page found"
        r"|is not titled|is not E\d+ banded|does not print on interior page"
        r"|is the blank title page|removed no ink"
        r"|AssertionError: assert \{|the pages that differ between a host)",
        "M10 medium-blind read returns EMPTY: the cell reads ink, text, rows or "
        "a caption off a page the reader can no longer see, and the expected "
        "side still describes the bitmap",
        "CARD-337 (its nine seams and four non-seam mechanisms); "
        "tests/test_book_interior_type_floor.py's share is the third population, "
        "also CARD-337's",
    ),
    # ---------------------------------------------------------------- M11
    (
        # Read off a real ERRORS-section cause, never guessed: this is one of
        # the 23 reds the pre-``error_causes()`` walk could not see (the other
        # 21 are the ContentStream AttributeError M7d already names).
        r"test_book_pdf_band\.py: ERROR at setup: assert \d+ == \(\d+ \+ 1\)",
        "M11 raster page-write counter collapses IN A FIXTURE: band_draws "
        "asserts len(writes) == ONCE_PAGE_COUNT + 1 over _write_page calls, and "
        "a vector interior writes its pages as operators, so only the cover's "
        "write is counted (5 of 15) -- a medium-blind read that ERRORS its "
        "whole class instead of failing one cell",
        "CARD-337 (tests/test_book_pdf_band.py is in its population A; the "
        "module fixture's seam, not a cell's)",
    ),
]

LINE = re.compile(r"^\s*x(\d+)\s+\[(delitem|conversion)\]\s+(.*)$")
#: Anything shaped like a cause line. A line matching this but NOT ``LINE`` is
#: a malformed dump entry, reported rather than skipped -- the silent
#: ``continue`` it replaces is how 23 reds went unseen.
CAUSE_SHAPED = re.compile(r"^\s*x\d+\s+\[")
MODULE = re.compile(r"^(RED|gree)\s+(\S+)")
#: The census's own red count per module, used to cross-check this walk's
#: coverage instead of trusting it.
MODULE_RED = re.compile(r"\bred=(\d+)\b")


def classify(cause: str) -> tuple[str, str] | None:
    for pattern, mechanism, owner in RULES:
        if re.search(pattern, cause):
            return mechanism, owner
    return None


def main() -> int:
    dump = Path(sys.argv[1])
    text = dump.read_text()
    assert text.strip(), f"{dump} is empty -- nothing to classify"

    module = "?"
    groups: collections.Counter = collections.Counter()
    owners: dict[str, str] = {}
    unclassified: list[tuple[str, str, int]] = []
    malformed: list[str] = []
    census_red = 0
    total = 0
    for raw in text.splitlines():
        header = MODULE.match(raw)
        if header:
            module = header.group(2)
            said = MODULE_RED.search(raw)
            census_red += int(said.group(1)) if said else 0
            continue
        found = LINE.match(raw)
        if not found:
            if CAUSE_SHAPED.match(raw):
                malformed.append(raw.strip())
            continue
        count, _tag, cause = int(found.group(1)), found.group(2), found.group(3)
        total += count
        verdict = classify(cause)
        if verdict is None:
            unclassified.append((module, cause, count))
            continue
        mechanism, owner = verdict
        groups[mechanism] += count
        owners[mechanism] = owner

    print(f"dump: {dump}")
    print(f"reds classified: {total}  (census counted {census_red})\n")
    for mechanism, count in groups.most_common():
        print(f"  x{count:<5} {mechanism}")
        print(f"          owner: {owners[mechanism]}")
    if unclassified:
        print(f"\nUNCLASSIFIED ({sum(n for _m, _c, n in unclassified)} reds, "
              f"{len(unclassified)} distinct causes) -- AC-3: each is a FINDING")
        for module, cause, count in unclassified:
            print(f"  x{count:<4} {module}\n        {cause[:200]}")
        return 1
    if malformed:
        print(f"\nMALFORMED ({len(malformed)} dump lines look like cause lines "
              f"and do not parse) -- skipping these silently is how a red hides")
        for raw in malformed:
            print(f"  {raw[:200]}")
        return 1
    if census_red and total != census_red:
        print(f"\nSHORTFALL: this walk classified {total} reds, the census "
              f"counted {census_red}. The difference is unseen, not 'other' "
              f"(AC-3). Re-run the census -- it exits non-zero on any "
              f"unaccounted red of its own.")
        return 1
    print(f"\nOK: every red carries a mechanism and an owner; no 'other' group "
          f"({total} classified, {census_red} counted by the census)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
