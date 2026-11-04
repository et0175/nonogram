"""CARD-337 re-cut hand-off: the mechanism x module cross-tab, re-derived.

Not a test and not under ``tests/`` (G-8). It runs **no pytest**: it is a pure
function of a census dump that already exists, so it needs no full-suite lock.

**It does not restate CARD-338's rules, it IMPORTS them.** ``classify_reds.py``
owns the mechanism taxonomy, its ordering ("first match wins") and its owners;
a second transcription of that table here is how two cards end up disagreeing
about what M7 means. The only thing added is the second axis -- the module --
which ``classify_reds.py`` reads into a variable and then does not group by.

Reconciliation is asserted in **both** directions and in **both** margins, per
ADR-0039/R2 (a shape the walk cannot classify is a FAILURE, never a bucket):

* every cause line must match a rule -- an unclassified cause exits non-zero;
* the row totals must sum to the same figure as the column totals;
* that figure must equal the census's own ``red=`` column, summed.

Run::

    python scratchpad/card337/cross_tab.py <dump.txt>
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "card338"))

# CARD-338's taxonomy, imported rather than retyped.
from classify_reds import (  # noqa: E402
    CAUSE_SHAPED,
    LINE,
    MODULE,
    MODULE_RED,
    RULES,
    classify,
)

TAG = re.compile(r"^(M\d+[a-z]?)\b")


def main() -> int:
    dump = Path(sys.argv[1])
    text = dump.read_text()
    assert text.strip(), f"{dump} is empty -- nothing to classify"

    module = "?"
    cell: collections.Counter = collections.Counter()   # (tag, module) -> reds
    by_tag: collections.Counter = collections.Counter()
    by_module: collections.Counter = collections.Counter()
    census_red: collections.Counter = collections.Counter()
    label: dict[str, str] = {}
    owner: dict[str, str] = {}
    signatures: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    unclassified: list[tuple[str, str, int]] = []
    malformed: list[str] = []

    for raw in text.splitlines():
        header = MODULE.match(raw)
        if header:
            module = header.group(2)
            said = MODULE_RED.search(raw)
            census_red[module] += int(said.group(1)) if said else 0
            continue
        found = LINE.match(raw)
        if not found:
            if CAUSE_SHAPED.match(raw):
                malformed.append(raw.strip())
            continue
        count, cause = int(found.group(1)), found.group(3)
        verdict = classify(cause)
        if verdict is None:
            unclassified.append((module, cause, count))
            continue
        mechanism, who = verdict
        tag = TAG.match(mechanism)
        assert tag, f"mechanism label does not start with an M-tag: {mechanism!r}"
        key = tag.group(1)
        label[key] = mechanism
        owner[key] = who
        cell[(key, module)] += count
        by_tag[key] += count
        by_module[module] += count
        signatures[key][cause] += count

    if unclassified:
        print(f"FAIL: {sum(n for *_x, n in unclassified)} red(s) carry no "
              f"mechanism -- a FINDING, not a bucket (ADR-0039/R2)")
        for mod, cause, count in unclassified:
            print(f"  x{count:<4} {mod}\n        {cause[:200]}")
        return 1
    if malformed:
        print(f"FAIL: {len(malformed)} dump line(s) look like cause lines and "
              f"do not parse")
        for raw in malformed:
            print(f"  {raw[:200]}")
        return 1

    modules = sorted(census_red, key=lambda m: (-census_red[m], m))
    tags = sorted(by_tag, key=lambda t: (-by_tag[t], t))

    print(f"dump: {dump}\n")
    print("=== MECHANISM x MODULE (reds)\n")
    # Short column keys, assigned so they are UNIQUE: truncating the file
    # names collides (`export_interior_cover` and
    # `property/test_book_export_interior` share a 13-character prefix), and a
    # cross-tab whose columns cannot be told apart cannot scope a Touches
    # field. A collision is a FAILURE here, not a narrower label.
    short: dict[str, str] = {}
    for index, m in enumerate(modules, start=1):
        stem = Path(m).name.replace("test_book_", "").replace(".py", "")
        if m.startswith("tests/property/"):
            stem = "prop:" + stem
        short[m] = f"C{index}"
        print(f"    C{index:<3} = {m}   ({stem})")
    assert len(set(short.values())) == len(modules), "column keys collide"
    print()
    head = "".join(f"{short[m]:>7}" for m in modules)
    print(f"{'mech':6}{head}{'TOTAL':>8}")
    for tag in tags:
        row = "".join(
            f"{cell[(tag, m)] or '.':>7}" for m in modules
        )
        print(f"{tag:6}{row}{by_tag[tag]:>8}")
    foot = "".join(f"{by_module[m]:>7}" for m in modules)
    print(f"{'TOTAL':6}{foot}{sum(by_tag.values()):>8}")

    print("\n=== PER MECHANISM: modules, owner, and the cause signature the "
          "gate prints\n")
    for tag in tags:
        where = sorted(
            ((m, n) for (t, m), n in cell.items() if t == tag),
            key=lambda pair: (-pair[1], pair[0]),
        )
        print(f"{tag}  ({by_tag[tag]} reds, {len(where)} module(s))")
        print(f"    label: {label[tag]}")
        print(f"    owner (CARD-338's attribution): {owner[tag]}")
        print(f"    modules: " + ", ".join(f"{m} x{n}" for m, n in where))
        said = signatures[tag]
        print(f"    distinct cause lines: {len(said)}")
        for cause, n in said.most_common(3):
            print(f"      x{n:<4} {cause[:150]}")
        print()

    print("=== RECONCILIATION (both margins, and against the census)")
    rows = sum(by_tag.values())
    cols = sum(by_module.values())
    says = sum(census_red.values())
    print(f"    row totals sum:      {rows}")
    print(f"    column totals sum:   {cols}")
    print(f"    census red= column:  {says}")
    ok = rows == cols == says
    for mod in modules:
        if by_module[mod] != census_red[mod]:
            print(f"    MISMATCH {mod}: cross-tab {by_module[mod]} vs census "
                  f"{census_red[mod]}")
            ok = False
    if not ok:
        print("\nFAIL: the margins do not reconcile. The table is NOT usable "
              "for scoping a Touches field -- fix the walk, never patch the "
              "table.")
        return 1
    print(f"\nOK: both margins and the census agree at {rows}.")

    print("\n=== MODULES WHOSE REDS SPLIT ACROSS MECHANISMS (the conflict "
          "question)\n")
    for mod in modules:
        here = sorted(
            ((t, n) for (t, m), n in cell.items() if m == mod),
            key=lambda pair: (-pair[1], pair[0]),
        )
        flag = "SPLIT" if len(here) > 1 else "single"
        print(f"  [{flag:6}] {mod:48} "
              + ", ".join(f"{t}x{n}" for t, n in here))

    # ---------------------------------------------------------------- the
    # question that decides whether the new cards can run concurrently: do two
    # of them have to touch the same file? Derived from the cross-tab, with the
    # groupings stated as data so a re-grouping is one edit and not a re-read.
    print("\n=== PROPOSED CARDS: module sets and pairwise COLLISIONS\n")
    groups = {
        "CARD-337 (re-cut)": ("M6", "M6b"),
        "CARD-354": ("M10",),
        "CARD-355": ("M7d",),
        "CARD-356": ("M7", "M7b"),
        "CARD-357": ("M9", "M11"),
        "CARD-322": ("M1", "M2", "M3", "M3b"),
        "CARD-336": ("M8",),
    }
    placed = {t for tags_ in groups.values() for t in tags_}
    missing = sorted(set(by_tag) - placed)
    assert not missing, (
        f"{missing} is in the cross-tab and in no proposed card: a mechanism "
        f"with no owner is the 'other' bucket under another name"
    )
    unknown = sorted(placed - set(by_tag))
    assert not unknown, (
        f"{unknown} is named by a proposed card and has NO reds in this "
        f"cross-tab: that card would be cut against nothing"
    )
    owns: dict[str, dict[str, int]] = {}
    for card, tags_ in groups.items():
        here: collections.Counter = collections.Counter()
        for tag in tags_:
            for (t, m), n in cell.items():
                if t == tag:
                    here[m] += n
        owns[card] = dict(here)
        print(f"  {card:20} {sum(here.values()):>4} reds in "
              f"{len(here)} module(s): "
              + ", ".join(f"{Path(m).name} x{n}"
                          for m, n in sorted(here.items(),
                                             key=lambda kv: -kv[1])))
    names = list(groups)
    print()
    print(f"{'':20}" + "".join(f"{n.split()[0][-3:]:>7}" for n in names))
    for left in names:
        row = ""
        for right in names:
            if left == right:
                row += f"{'-':>7}"
            else:
                shared = set(owns[left]) & set(owns[right])
                row += f"{len(shared) or '.':>7}"
        print(f"{left:20}{row}")
    print("\n  (cell = how many FILES the two cards would both have to edit; "
          "`.` = none, so they can run concurrently)")
    exclusive = {
        card: [m for m in owns[card]
               if not any(m in owns[other] for other in names if other != card)]
        for card in names
    }
    print("\n  modules owned EXCLUSIVELY by one card:")
    for card in names:
        print(f"    {card:20} {len(exclusive[card])}: "
              + (", ".join(Path(m).name for m in exclusive[card]) or "NONE"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
