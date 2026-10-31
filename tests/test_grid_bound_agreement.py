"""CARD-317/AC-3 — the supported grid bound, held to one number everywhere.

Three artefacts state the bound and until this module nothing compared them:

* ``src/nonogram/limits.py`` — ``MIN_SIZE``/``MAX_SIZE``, the authority;
* ``meta/architecture/requirements.yml`` — FR-019's statement and AC-068's
  boundary criterion, the live registry entries (FR-001's are retired and say
  50x50 on purpose; see the third cell);
* ``meta/architecture/decisions/adr/0001-generation-time-thresholds.md`` — the
  ADR that caps generation time *up to the maximum supported size*, and whose
  text named 50x50 for 62 days after the range narrowed to 30.

**Why a test and not a note.** The divergence CARD-317 reconciled was readable
in all three files and visible to nobody, because reading them together was
nobody's job. The 50-vs-30 contradiction was not a hidden fact: it was an
uncompared one. A comparison is the only artefact that cannot stop being made.

**Deliberately no YAML parser.** The suite ships none (the dependency baseline
is stdlib + Pillow + NumPy, ADR-0006/R1, and ``tests/test_check_ref_resolution``
reads the same registry as lines for the same reason), so the registry is
scanned as text. That makes the scanner itself a claim, so it is proved in both
directions by :func:`test_the_registry_scanner_is_proved_in_both_directions`
before anything is concluded from it: an instrument that silently finds nothing
reads exactly like a clean verdict (CARD-317's G-3).

**No number below is written twice.** Every figure is read from one of the three
artefacts at run time; the only literals here are the *shapes* being searched
for and the retraction cues the ADR is allowed to carry.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nonogram import limits

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "meta" / "architecture" / "requirements.yml"
ADR_0001 = (
    REPO_ROOT
    / "meta"
    / "architecture"
    / "decisions"
    / "adr"
    / "0001-generation-time-thresholds.md"
)

#: ``NxN`` as the model writes a square extent.
_SQUARE = re.compile(r"\b([0-9]{1,3})x([0-9]{1,3})\b")

#: FR-019's statement spells the range in words, not as ``NxN``.
_SIDE_RANGE = re.compile(r"each side ([0-9]{1,3}) to ([0-9]{1,3}) inclusive")

#: The id line of a top-level requirement, and of one of its criteria. The
#: indentation is the registry's and is what tells the two apart.
_REQ_ID = re.compile(r"^  - id: ([A-Z]+-[0-9]+)\s*$")
_CRIT_ID = re.compile(r"^      - id: (AC-[0-9]+)\s*$")


def _lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise AssertionError(f"{path} is empty -- nothing could be compared")
    return text.splitlines()


def _requirement_block(lines: list[str], req_id: str) -> list[str]:
    """The lines of one requirement entry, id line included.

    Raises rather than returning empty: a requirement the scanner cannot find
    is a scanner that reports agreement about nothing.
    """
    start = None
    for index, line in enumerate(lines):
        match = _REQ_ID.match(line)
        if match and match.group(1) == req_id:
            start = index
            break
    if start is None:
        raise AssertionError(f"{req_id} was not found in the registry")
    for index in range(start + 1, len(lines)):
        if _REQ_ID.match(lines[index]):
            return lines[start:index]
    return lines[start:]


def _criteria(block: list[str]) -> dict[str, list[str]]:
    """``AC-id -> its lines`` for one requirement block, in declared order."""
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in block:
        match = _CRIT_ID.match(line)
        if match:
            current = match.group(1)
            found[current] = [line]
        elif current is not None:
            if line.startswith("    ") and not line.startswith("      "):
                current = None          # left the acceptance list entirely
            else:
                found[current].append(line)
    return found


def _field(crit_lines: list[str], key: str) -> str | None:
    """One scalar field of a criterion, or ``None`` when it carries none."""
    marker = f"        {key}: "
    for line in crit_lines:
        if line.startswith(marker):
            return line[len(marker) :].strip()
    return None


# --------------------------------------------------------------------------
# The scanner, proved before it is believed
# --------------------------------------------------------------------------


def test_the_registry_scanner_is_proved_in_both_directions() -> None:
    """G-3: it finds what is there and refuses what is not.

    Both halves on the real file. The positive half is the one the two cells
    below rest on; the negative half is why an empty result cannot be read as
    agreement.
    """
    lines = _lines(REQUIREMENTS)

    live = _requirement_block(lines, "FR-019")
    assert live[0].strip() == "- id: FR-019"
    criteria = _criteria(live)
    assert set(criteria) == {"AC-066", "AC-067", "AC-068", "AC-069", "AC-070"}, (
        sorted(criteria)
    )
    assert _field(criteria["AC-068"], "kind") == "boundary"

    with pytest.raises(AssertionError, match="FR-9999"):
        _requirement_block(lines, "FR-9999")
    # A field no criterion carries reads as absent, never as a stray match from
    # a neighbouring line.
    assert _field(criteria["AC-066"], "superseded_by") is None


# --------------------------------------------------------------------------
# AC-3 — one number in three places
# --------------------------------------------------------------------------


def test_the_live_registry_bound_is_the_constant() -> None:
    """FR-019's statement and AC-068's extent equal ``limits``' own range.

    Read three ways from two places, and compared with the constants rather
    than derived from them: the statement's worded range, the ``given`` of the
    boundary criterion, and its ``then``. A drift in any one of the three reds
    here, which is what "the two cannot drift apart again silently" needs.
    """
    block = _requirement_block(_lines(REQUIREMENTS), "FR-019")
    statement = " ".join(line.strip() for line in block)

    worded = _SIDE_RANGE.search(statement)
    assert worded, f"FR-019's statement no longer spells its side range: {statement}"
    assert (int(worded.group(1)), int(worded.group(2))) == (
        limits.MIN_SIZE,
        limits.MAX_SIZE,
    ), (worded.group(0), limits.MIN_SIZE, limits.MAX_SIZE)

    criterion = _criteria(block)["AC-068"]
    for key in ("given", "then"):
        text = _field(criterion, key)
        assert text, f"AC-068 has no {key}"
        extents = _SQUARE.findall(text)
        assert extents, f"AC-068's {key} names no NxN extent: {text}"
        assert all(
            (int(width), int(height)) == (limits.MAX_SIZE, limits.MAX_SIZE)
            for width, height in extents
        ), (key, extents, limits.MAX_SIZE)


#: A sentence boundary as this ADR writes one: terminal punctuation then space.
#: The ADR's paragraphs are single lines of a thousand characters and more, so
#: the unit of the scan below has to be smaller than a line -- see that cell's
#: docstring for the measurement that forced this.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


def test_adr_0001_names_no_bare_maximum_other_than_the_constant() -> None:
    """ADR-0001's text agrees with the constant, or says where it does not.

    The ADR decides two *durations* and caps the second "up to the maximum
    supported size", so it necessarily names an extent, and it was written
    against 50x50. Its historical sentences are kept — that record is the
    point of CARD-317's G-1 — so the rule asserted here is not "the string
    50x50 is absent" but the weaker, true one: **every SENTENCE naming a
    square extent other than the constant's also carries a retraction cue**.

    **Scoped to sentences, not lines — CARD-317 review cycle 1, F-004.** This
    cell shipped line-scoped, and its docstring claimed what sentence scope
    buys while only line scope was implemented. Measured by the reviewer and
    reproduced here: a cue-free *new line* claiming a 50x50 maximum was killed,
    but the same sentence appended inside the **Decision** paragraph survived,
    because that paragraph is one ~1000-character line that already carries
    "narrowed" and "History" — and the Decision paragraph is exactly where a
    future reaffirmation would be written. One cue anywhere in a multi-sentence
    paragraph was exempting every stale extent in it.

    **What is still not caught, stated rather than implied.** A stale extent
    spliced *inside* an existing cue-bearing sentence — no terminal
    punctuation between the cue and the extent — still passes, and so does one
    in a paragraph written as a single sentence. Sentence scope is the
    narrowest unit a text scan can draw without a parser; the claim here is
    exactly "cue in the same sentence", not "cue near the extent".
    """
    cues = (
        "superseded",
        "since 2026-08-30",
        "not the 50x50",
        "when this was written",
        "when this was decided",
        "narrowed",
        "retired",
        "alternative not taken",
        "History",
    )
    # Each cue above is a phrase that RETRACTS the extent in its own sentence,
    # and the set is deliberately short: every addition is a hole. "retired"
    # earned its place by catching this card's own History entry. "alternative
    # not taken" earned its place when the scope narrowed to sentences: the
    # History entry's two rejected-alternative sentences name 50x50 and carry
    # their retraction in that phrase alone, their paragraph's "retired" and
    # "narrowed" being in other sentences. Measured, not assumed — the
    # sentence scan over the real file reports six sentences holding a stale
    # extent, and this is the one cue none of the other eight covers.
    offenders = []
    seen_any = False
    for number, line in enumerate(_lines(ADR_0001), start=1):
        if not _SQUARE.search(line):
            continue
        for sentence in _SENTENCE_BREAK.split(line):
            extents = {
                (int(width), int(height))
                for width, height in _SQUARE.findall(sentence)
            }
            if not extents:
                continue
            seen_any = True
            stale = {
                extent
                for extent in extents
                if extent[0] == extent[1] and extent[0] > limits.MAX_SIZE
            }
            if stale and not any(cue in sentence for cue in cues):
                offenders.append((number, sorted(stale), sentence.strip()[:160]))

    assert seen_any, "ADR-0001 names no square extent at all -- the scan read nothing"
    assert not offenders, (
        "ADR-0001 states a maximum above limits.MAX_SIZE="
        f"{limits.MAX_SIZE} in a sentence with nothing in it to retract it:\n"
        + "\n".join(f"  line {n}: {ext} -- {text}" for n, ext, text in offenders)
    )


def test_the_retired_criteria_of_fr_001_are_marked_retired() -> None:
    """FR-001's four criteria stay machine-readably superseded.

    They say 50x50 deliberately and keep refs that resolve to nothing
    deliberately — the supersession is reversible only while the original text
    survives. What this pins is the half that is *not* prose: each carries
    ``status: superseded`` and a ``superseded_by`` naming a criterion FR-019
    actually declares. Un-stamp any one of them and it goes back to reading as
    a live, unverified claim that the tool counts, which is the state CARD-317
    found the registry in.
    """
    lines = _lines(REQUIREMENTS)
    retired = _criteria(_requirement_block(lines, "FR-001"))
    live = set(_criteria(_requirement_block(lines, "FR-019")))

    assert set(retired) == {"AC-001", "AC-002", "AC-003", "AC-004"}, sorted(retired)
    for ac_id, crit in sorted(retired.items()):
        assert _field(crit, "status") == "superseded", (ac_id, _field(crit, "status"))
        successor = _field(crit, "superseded_by")
        assert successor in live, (ac_id, successor, sorted(live))
