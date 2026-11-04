"""CARD-363 — the two inputs of the retrospective's cycle ratio, guarded.

``forge:retrospective``'s ``accuracy_ratio`` is ``cycles_used /
estimate_cycles`` (ADR-0055, cited on the board — see "The decision has no ADR
file" below). Both terms are read out of a card file, and until this module
existed neither was checked:

**The numerator.** ``cycles_used`` is the COUNT of ``[Review N/M] Score:``
lines in a card's ``## Worktree notes``. Nothing writes that marker reliably
and nothing ever compared it against the cycle the card's own ``Review score``
field names. Measured here on the whole card tree: of 231 ``done`` cards
carrying a numeric score, **128 carry no marker at all** and **50 carry a
number that disagrees** with the cycle their score states. The marker is the
weaker record of the two — and it is the only one the extractor reads.

**The denominator.** ``estimate_cycles`` is an ``Nc`` term in ``Estimate``.
Nothing required a card that ran in a wave to carry one. Waves 71–73 exported
no calibration signal for exactly this reason: they had the cycle count all
along and no cycle estimate to divide it by. The unit of the estimate is the
scarce input, and it is the one this module's second guard pins.

The live harm, for the record
=============================
CARD-337's merge gate found that card's estimate in three disagreeing copies —
the card said ``1c``, ``meta/kanban/board.md`` said ``2c``, and
``meta/kanban/dispatcher.state`` said ``2c (2d)``. The card was authoritative
(re-estimated at a re-cut); the other two predate it and were never updated. A
retrospective reading the board rather than the card would have computed 0.500
for a card priced and delivered at one cycle. **This module does not guard that
three-copy disagreement** — it is a different surface, and naming it here is
deliberate so the omission is met rather than discovered. What it guards is the
unit, which is what makes the copies comparable at all.

Why this reads card bodies and nothing else (AC-5)
==================================================
Every datum here comes from ``meta/kanban/cards/CARD-*.md``, which are tracked.
:func:`test_the_guards_read_only_tracked_files` proves it twice: dynamically,
by asserting every path :func:`read_card_tree` opened is in ``git ls-files``,
and statically, by walking this module with ``ast`` for a non-docstring string
literal naming ``meta/review``.

**And the card's stated reason for that constraint is false, measured.**
CARD-363 says the review YAMLs "are untracked by convention and absent from a
fresh clone". ``meta/review/*.yml`` does match ``.gitignore:102`` — and **396
of them are tracked anyway**, so they would be present in a fresh clone. (That
is the same ignored-yet-tracked set ``tests/test_check_ref_resolution.py``
counts, and the mechanism behind this board's "review YAMLs revive dead check
refs" finding.) The constraint still holds and is still worth asserting — a
guard over the board's bookkeeping should not depend on a path the project
deliberately ignores — but it holds for a reason the card got wrong, so it is
asserted here directly rather than inherited.

The decision has no ADR file
============================
``ADR-0055`` is cited by ``meta/kanban/board.md``,
``meta/kanban/dispatcher.state``, ``meta/kanban/retro.md``, CARD-363 and
CARD-366. **There is no such file**: ``meta/architecture/decisions/adr/`` tops
out at ``0042``. So the forward boundary below is named after the measured
convention rather than after the dangling ref, and
:func:`test_the_estimate_unit_decision_still_has_no_adr_file` pins the absence
so that writing the ADR reds here and sends its author to the constant.

Two parsing traps, both measured on this tree
=============================================
**1. A field value can carry an inline HTML comment.** The card format's field
parse (reimplemented in :func:`parse_card_fields`; see "Why reimplemented")
strips none, so ``**Estimate:** 2c (1d) <!-- … -->`` parses as the whole
string including the comment. Measured on this tree: **7** cards carry a
comment inside ``Estimate`` and **15** inside ``Wave``. Interpreting a field
therefore means stripping comments first — and *checking* for contamination
means asserting on the RAW value, because a check that strips before looking
cannot see what it is looking for. Both halves are asserted:
:func:`test_an_inline_comment_contaminates_the_raw_field_value` reads raw,
:func:`test_the_wave_and_estimate_readings_strip_comments_first` reads stripped.

**2. The score field has at least five cycle spellings, and neither the first
nor the last number in it is the answer.** Measured frequencies over the 231
scored cards: ``cycle N/M`` dominates (169), ``cycle N of M`` is rare (19),
and there are also bare ``cycle N``, ``cN`` / ``cN/M``, and ``N cycles``
forms. Two independent ways to get it wrong, both measured here rather than
asserted:

* **first ordinal** — wrong on the progression format, where the score field
  records the whole trajectory: ``8.0 (c1) → 8.5 (c2) → 8.0 (c3/3)`` is cycle
  3, and a parser taking the first number gets 1 (and, reading the score
  itself, 8.0 instead of the final 8.0 — CARD-239 is the sharp case, where
  first gives 8.0 and the real final score is 7.5).
* **last ordinal** — wrong where the field names the final cycle first and
  then the earlier ones: ``8.0 (cycle 2; cycle 1 8.5)`` is cycle 2, and last
  gives 1.

:func:`test_cycle_named_beats_both_naive_readings_on_the_real_tree` derives how
many real cards each naive reading gets wrong and asserts both counts are
non-zero, so neither control can quietly stop discriminating.

**2b. The decimal point in the score is a word boundary.** This one cost a
cycle to find. A ``N cycles`` pattern written ``(\\d+)\\s+cycles?`` matches the
``0`` of ``9.0`` in CARD-301's ``7.0 → **9.0 cycle 2/3 CERTIFIED**`` — because
``.`` is not a word character — and, being the leftmost match, wins the
alternation and reports **cycle 0**. Hence the ``(?<![\\w.])`` lookbehind on
both cycle patterns, and :func:`test_the_decimal_score_does_not_leak_into_the_cycle`
keeps the naive spelling present as a control that still fails.

Why the parse is reimplemented and not imported
===============================================
``card_lint.parse_card_fields`` lives in ``/Users/omelnikova/MyProjects/forge_1``,
outside this repository and read-only, so it is not importable from the suite
and not editable from here. This module reimplements the field parse natively —
this tree's standing preference for a second implementation over a cross-import
(precedent: ``solver/propagate.py``'s ``mask_runs``). The reimplementation is
deliberately faithful on the two properties that matter: the header block only
(text before the first ``## ``), and last-write-wins.

What the figures in the card say, and what they are
===================================================
All five of CARD-363's figures were re-derived here and **four do not
reproduce**. The card's own PREMISE CORRECTED block confesses that one figure
was asserted rather than measured; the corrected replacement is wrong in the
same direction, and by the same mechanism — a regex narrower than the grammar.
The card's "71 cards whose score names no cycle" is **3**: the inflated figure
came from an inflated denominator (281, which counts 50 cards whose score field
is a prose *"merged without a review cycle, at the owner's call"* sentinel and
not a score at all) combined with a ``cycle N of M`` reading that misses the
169 cards spelling it ``cycle N/M``. The direction of the card's argument
survives intact: the score field covers 228 of 231 where the marker covers
103, so the score remains much the better source.

The figures asserted below are this module's own measurements. **Re-derive
them; never paste a failure's printed number back in** — that is how this
board's censuses rot.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The one directory any guard in this module reads. Tracked; see AC-5.
CARDS_DIR = REPO_ROOT / "meta" / "kanban" / "cards"

#: The first wave whose cards were estimated in review cycles. Wave 74's
#: estimates were restated as ``Nc`` at the wave open — a decision made before
#: any work happened — and that, not the writing of markers, is why wave 74 is
#: the first wave from which a cycle ratio was computable. Named after the
#: measured convention rather than after ``ADR-0055``, which has no file.
ESTIMATE_UNIT_FIRST_WAVE = 74

# --------------------------------------------------------------------------
# Field and body parsing
# --------------------------------------------------------------------------

_FIELD_LINE = re.compile(r"^\*\*([A-Za-z][A-Za-z ]*):\*\*\s*(.*)$")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

#: The ONE marker ``cmd-review-cycle``'s sync point writes once per completed
#: review cycle, and the one quantity ``cycles_used`` counts. A leading list
#: bullet is tolerated (older cards bullet their notes); a marker that drops or
#: displaces the ``/M`` denominator is not matched, which is the retrospective
#: extraction's own disclosed rule, restated here rather than widened.
_MARKER = re.compile(r"^\s*(?:[-*+]\s+)?\[Review (\d+)/(\d+)\] Score:")

#: A numeric score in the ``Review score`` field. Its absence is what separates
#: a reviewed card from one merged on the owner's call with a prose sentinel.
_SCORE_VALUE = re.compile(r"\d+\.\d+")

#: An explicit cycle ORDINAL: ``cycle 3``, ``cycle 2/3``, ``cycle 3 of 3``,
#: ``c2``, ``c3/3``. The lookbehind is load-bearing — see trap 2b.
_CYCLE_ORDINAL = re.compile(r"(?<![\w.])(?:cycle\s+|c)(\d+)\b", re.I)

#: A cycle COUNT: ``2 cycles``, ``1 cycle + fix``. Consulted only when no
#: ordinal is present, so ``9.0 (cycle 2/3)`` is never read as a count.
_CYCLE_COUNT = re.compile(r"(?<![\w.])(\d+)\s+cycles?\b", re.I)

#: The naive spelling of :data:`_CYCLE_COUNT`, kept as a control that fails.
_CYCLE_COUNT_NAIVE = re.compile(r"(\d+)\s+cycles?\b", re.I)

#: The card-format reading of ``cycle N of M`` alone — the spelling CARD-363's
#: own premise was measured with. Kept as a control: it misses the majority.
_CYCLE_N_OF_M_ONLY = re.compile(r"\bcycle\s+(\d+)\s+of\s+(\d+)\b", re.I)

_LEADING_WAVE = re.compile(r"^(\d+)\b")

#: An ``Nc`` term in ``Estimate``: ``2c (1d)``, ``1c (0.25d)``.
_ESTIMATE_CYCLES = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*c\b")

_WORKTREE_NOTES_HEADING = re.compile(r"^## Worktree notes\s*$", re.M)
_ANY_HEADING = re.compile(r"^## ", re.M)

_DASH = "—"  # the card format's own "no value" token


def header_block(text: str) -> str:
    """The text before the first ``## `` heading — where fields live.

    Faithful to ``card_lint._header_block``: a field-shaped line further down
    a card (``**FR:**`` inside a prose section) must not be read as a field.
    """
    index = text.find("\n## ")
    return text if index == -1 else text[:index]


def parse_card_fields(text: str) -> dict[str, str]:
    """Every ``**Field:** value`` line of the header block, last-write-wins.

    Values are returned **exactly as written** — HTML comments included. That
    is the behaviour the real parser has, and preserving it here is what lets
    :func:`test_an_inline_comment_contaminates_the_raw_field_value` assert on
    the contamination instead of on a cleaned-up copy of it.
    """
    fields: dict[str, str] = {}
    for line in header_block(text).splitlines():
        match = _FIELD_LINE.match(line.strip())
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def strip_comments(value: str) -> str:
    """``value`` with every HTML comment removed, whitespace collapsed."""
    return _HTML_COMMENT.sub("", value).strip()


def worktree_notes(text: str) -> str | None:
    """The ``## Worktree notes`` section, or ``None`` if the card has none.

    ``None`` is not "no markers": it is a card whose marker count the
    retrospective's extraction has nowhere to read, and this module classifies
    it :data:`UNCLASSIFIABLE` rather than folding it in as zero.
    """
    heading = _WORKTREE_NOTES_HEADING.search(text)
    if heading is None:
        return None
    rest = text[heading.end() :]
    following = _ANY_HEADING.search(rest)
    return rest if following is None else rest[: following.start()]


def marker_count(text: str) -> int | None:
    """``cycles_used`` as the retrospective extracts it, or ``None``.

    Counted inside ``## Worktree notes`` only, because that is where the
    extraction looks. Measured consequence, declared by
    :func:`test_declared_bound_markers_written_outside_the_worktree_notes`:
    16 cards carry a Score marker elsewhere in the body, where the extraction
    cannot see it.
    """
    section = worktree_notes(text)
    if section is None:
        return None
    return sum(1 for line in section.splitlines() if _MARKER.match(line))


def cycle_ordinals(score: str) -> tuple[int, ...]:
    """Every cycle number the score field names, in the order written."""
    ordinals = tuple(int(m.group(1)) for m in _CYCLE_ORDINAL.finditer(score))
    if ordinals:
        return ordinals
    return tuple(int(m.group(1)) for m in _CYCLE_COUNT.finditer(score))


def cycle_named(score: str) -> int | None:
    """The review cycle the score field names, or ``None`` if it names none.

    The **maximum** ordinal, not the first and not the last: both of those are
    wrong on real cards of this board, in opposite directions, and
    :func:`test_cycle_named_beats_both_naive_readings_on_the_real_tree`
    measures how often.
    """
    ordinals = cycle_ordinals(score)
    return max(ordinals) if ordinals else None


def estimate_cycles(estimate: str) -> float | None:
    """The ``Nc`` term of an ``Estimate``, comments stripped, or ``None``."""
    match = _ESTIMATE_CYCLES.search(strip_comments(estimate))
    return float(match.group(1)) if match else None


def card_wave(wave: str) -> int | None:
    """The wave a card ran in, or ``None`` for ``—``/``unscheduled``.

    Comments are stripped first: 15 cards carry a dispatch note inside the
    value, and ``"76 <!-- … -->"`` is not an integer.
    """
    match = _LEADING_WAVE.match(strip_comments(wave))
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------
# The derived card tree (ADR-0039/R2: the set is enumerated, never listed)
# --------------------------------------------------------------------------

AGREES = "AGREES"
NO_MARKER = "NO_MARKER"
MARKER_DISAGREES = "MARKER_DISAGREES"
SCORE_NAMES_NO_CYCLE = "SCORE_NAMES_NO_CYCLE"
UNCLASSIFIABLE = "UNCLASSIFIABLE"

#: Every class a scored card can land in. The five partition the population;
#: :func:`test_every_scored_card_lands_in_exactly_one_class` asserts it.
CLASSES = (AGREES, NO_MARKER, MARKER_DISAGREES, SCORE_NAMES_NO_CYCLE, UNCLASSIFIABLE)


@dataclass(frozen=True)
class Card:
    """One card file, read once."""

    name: str
    path: Path
    text: str
    fields: dict[str, str]

    @property
    def raw_score(self) -> str:
        return self.fields.get("Review score", "")

    @property
    def raw_estimate(self) -> str:
        return self.fields.get("Estimate", "")

    @property
    def raw_wave(self) -> str:
        return self.fields.get("Wave", "")

    @property
    def status(self) -> str:
        return strip_comments(self.fields.get("Status", ""))

    @property
    def wave(self) -> int | None:
        return card_wave(self.raw_wave)

    @property
    def is_scored(self) -> bool:
        """A numeric review score, as opposed to a ``—`` prose sentinel.

        50 ``done`` cards carry a sentence in this field instead of a score
        (*"merged without a review cycle, at the owner's call"*). They were
        never reviewed, so no cycle count exists for them to disagree with,
        and counting them as "scored" is what inflated CARD-363's denominator
        from 231 to 281.
        """
        return bool(_SCORE_VALUE.search(strip_comments(self.raw_score)))

    @property
    def cycle_named(self) -> int | None:
        return cycle_named(strip_comments(self.raw_score))

    @property
    def marker_count(self) -> int | None:
        return marker_count(self.text)

    @property
    def classification(self) -> str:
        """Which of :data:`CLASSES` this card is in. Never a skip.

        Ordering matters and is argued: a card whose score names no cycle is
        its own population, because "the marker equals the cycle the score
        names" is *undefined* for it — not satisfied, not violated. Silently
        dropping those is precisely the move that produced CARD-363's own bad
        figure, so they are classified, counted and declared.
        """
        named = self.cycle_named
        if named is None:
            return SCORE_NAMES_NO_CYCLE
        count = self.marker_count
        if count is None:
            return UNCLASSIFIABLE
        if count == 0:
            return NO_MARKER
        if count != named:
            return MARKER_DISAGREES
        return AGREES


def read_card_tree(cards_dir: Path = CARDS_DIR) -> tuple[Card, ...]:
    """Every card file under ``cards_dir``, parsed.

    The authority the guards are derived from (ADR-0039/R2). There is no list
    of card ids anywhere in this module.
    """
    cards = []
    for path in sorted(cards_dir.glob("CARD-*.md")):
        text = path.read_text(encoding="utf-8")
        cards.append(Card(path.name, path, text, parse_card_fields(text)))
    return tuple(cards)


def scored_cards(cards: tuple[Card, ...]) -> tuple[Card, ...]:
    """``done`` cards carrying a numeric review score."""
    return tuple(c for c in cards if c.status == "done" and c.is_scored)


def ran_in_a_wave(cards: tuple[Card, ...], first_wave: int) -> tuple[Card, ...]:
    """Cards stamped with a numeric ``Wave`` at or after ``first_wave``."""
    return tuple(c for c in cards if c.wave is not None and c.wave >= first_wave)


def by_class(cards: tuple[Card, ...]) -> dict[str, tuple[str, ...]]:
    """The scored population split into :data:`CLASSES`, by card name."""
    buckets: dict[str, list[str]] = {name: [] for name in CLASSES}
    for card in scored_cards(cards):
        buckets[card.classification].append(card.name)
    return {name: tuple(names) for name, names in buckets.items()}


# --------------------------------------------------------------------------
# The two guards, each a pure violations function so a plant can drive it
# --------------------------------------------------------------------------


def marker_disagreements(
    cards: tuple[Card, ...], first_wave: int = ESTIMATE_UNIT_FIRST_WAVE
) -> list[str]:
    """Guard 1 — the marker count agrees with the cycle the score names.

    Scoped to cards that ran at or after ``first_wave``. A card whose score
    names no cycle is out of this guard's domain by construction and is held
    instead by :func:`test_declared_bound_the_cards_whose_score_names_no_cycle`.
    """
    violations = []
    for card in ran_in_a_wave(cards, first_wave):
        if card.status != "done" or not card.is_scored:
            continue
        named = card.cycle_named
        if named is None:
            violations.append(
                f"{card.name}: ran in wave {card.wave} and its score names no "
                f"review cycle — {card.raw_score!r}"
            )
            continue
        count = card.marker_count
        if count is None:
            violations.append(
                f"{card.name}: ran in wave {card.wave} and has no "
                f"'## Worktree notes' section, so cycles_used is unreadable"
            )
            continue
        if count != named:
            violations.append(
                f"{card.name}: {count} '[Review N/M] Score:' marker(s) in "
                f"'## Worktree notes', but its score names cycle {named} "
                f"({card.raw_score[:60]!r})"
            )
    return violations


def waves_without_a_cycle_estimate(
    cards: tuple[Card, ...], first_wave: int = ESTIMATE_UNIT_FIRST_WAVE
) -> list[str]:
    """Guard 2 — a card that ran in a wave carries a cycle estimate."""
    violations = []
    for card in ran_in_a_wave(cards, first_wave):
        if estimate_cycles(card.raw_estimate) is None:
            violations.append(
                f"{card.name}: ran in wave {card.wave} with "
                f"Estimate {strip_comments(card.raw_estimate)!r}, which states "
                f"no 'Nc' term — accuracy_ratio has no denominator"
            )
    return violations


def unclassifiable_cards(cards: tuple[Card, ...]) -> list[str]:
    """Every scored card the walk cannot place. ADR-0039/R2: a FAILURE."""
    return [
        f"{c.name}: score {strip_comments(c.raw_score)[:50]!r} names cycle "
        f"{c.cycle_named} but the card has no '## Worktree notes' section, so "
        f"its marker count is neither zero nor a number"
        for c in scored_cards(cards)
        if c.classification == UNCLASSIFIABLE
    ]


# --------------------------------------------------------------------------
# Fixtures and plants
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tree() -> tuple[Card, ...]:
    """The real board's card tree, read once."""
    return read_card_tree()


def _copy_tree(tmp_path: Path, names: tuple[str, ...]) -> Path:
    """A synthetic card tree holding copies of real cards.

    Plants mutate copies. The board's own files are never written by this
    module — INV-023 keeps the card file off a card branch, and a test that
    edits ``meta/kanban/**`` in place would be a commit waiting to happen.
    """
    target = tmp_path / "cards"
    target.mkdir()
    for name in names:
        shutil.copy(CARDS_DIR / name, target / name)
    return target


def _replace_field(path: Path, field: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^\*\*{re.escape(field)}:\*\*.*$", re.M)
    assert pattern.search(text), f"{path.name} has no **{field}:** line to plant on"
    path.write_text(pattern.sub(f"**{field}:** {value}", text, count=1), encoding="utf-8")


def _tracked_paths() -> frozenset[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return frozenset(p for p in out.split("\0") if p)


# --------------------------------------------------------------------------
# AC-1 — the marker agrees with the score
# --------------------------------------------------------------------------


def test_the_marker_count_agrees_with_the_cycle_the_score_names(
    tree: tuple[Card, ...],
) -> None:
    """AC-1 — guard 1 on the real tree, and it is not vacuous.

    The floor assertion is the control against vacuity (ADR-0039/R1): a guard
    whose population silently empties passes forever. Stated as a floor and
    not an equality so that closing a card does not red it.
    """
    population = [
        c.name
        for c in ran_in_a_wave(tree, ESTIMATE_UNIT_FIRST_WAVE)
        if c.status == "done" and c.is_scored
    ]
    assert len(population) >= 5, (
        "guard 1 has gone vacuous: no card from wave "
        f"{ESTIMATE_UNIT_FIRST_WAVE} onwards is done-and-scored. Population: "
        f"{population}"
    )
    assert marker_disagreements(tree) == []


def test_a_planted_marker_disagreement_reds_by_name(tmp_path: Path) -> None:
    """AC-1's control: drop one marker from a real in-scope card.

    CARD-339 ran in wave 74, scores *cycle 2 of 3* and carries two markers.
    Deleting one makes the record claim a cycle it cannot evidence — exactly
    the shape the retrospective would read as ``cycles_used = 1``.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-339.md", "CARD-337.md"))
    control = read_card_tree(cards_dir)
    assert marker_disagreements(control) == [], "the unplanted copy must be green"
    assert [c.marker_count for c in control if c.name == "CARD-339.md"] == [2]

    planted = cards_dir / "CARD-339.md"
    lines = planted.read_text(encoding="utf-8").splitlines(keepends=True)
    dropped = [line for line in lines if not _MARKER.match(line)]
    assert len(lines) - len(dropped) == 2
    planted.write_text("".join(dropped + [lines[-1]]), encoding="utf-8")
    # put exactly one marker back, so the count is 1 against a named cycle 2
    one_back = next(line for line in lines if _MARKER.match(line))
    planted.write_text(
        planted.read_text(encoding="utf-8") + one_back, encoding="utf-8"
    )

    found = marker_disagreements(read_card_tree(cards_dir))
    assert len(found) == 1, found
    assert found[0].startswith("CARD-339.md:"), found
    assert "marker(s)" in found[0] and "cycle 2" in found[0], found


def test_a_planted_card_with_no_notes_section_reds_by_name(tmp_path: Path) -> None:
    """AC-1's second refusal arm: an in-scope card with nowhere to read from."""
    cards_dir = _copy_tree(tmp_path, ("CARD-337.md",))
    assert marker_disagreements(read_card_tree(cards_dir)) == []

    planted = cards_dir / "CARD-337.md"
    planted.write_text(
        planted.read_text(encoding="utf-8").replace("## Worktree notes", "## Notes"),
        encoding="utf-8",
    )
    found = marker_disagreements(read_card_tree(cards_dir))
    assert len(found) == 1 and found[0].startswith("CARD-337.md:"), found
    assert "cycles_used is unreadable" in found[0], found


# --------------------------------------------------------------------------
# AC-2 — a card that ran in a wave carries a cycle estimate
# --------------------------------------------------------------------------


def test_a_card_that_ran_in_a_wave_carries_a_cycle_estimate(
    tree: tuple[Card, ...],
) -> None:
    """AC-2 — guard 2 on the real tree, with the same anti-vacuity floor."""
    population = ran_in_a_wave(tree, ESTIMATE_UNIT_FIRST_WAVE)
    assert len(population) >= 7, (
        "guard 2 has gone vacuous: no card is stamped with a wave at or after "
        f"{ESTIMATE_UNIT_FIRST_WAVE}. Found: {[c.name for c in population]}"
    )
    assert waves_without_a_cycle_estimate(tree) == []


def test_a_planted_day_only_estimate_reds_by_name(tmp_path: Path) -> None:
    """AC-2's control: restate an in-scope estimate in days.

    ``0.5d`` is not a worse estimate than ``1c (0.5d)``; it is an estimate in
    the unit that made waves 71–73 export no signal at all.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-337.md", "CARD-339.md"))
    assert waves_without_a_cycle_estimate(read_card_tree(cards_dir)) == []

    _replace_field(cards_dir / "CARD-337.md", "Estimate", "0.5d")
    found = waves_without_a_cycle_estimate(read_card_tree(cards_dir))
    assert len(found) == 1, found
    assert found[0].startswith("CARD-337.md:"), found
    assert "no 'Nc' term" in found[0] and "'0.5d'" in found[0], found


def test_a_cycle_estimate_hidden_behind_an_inline_comment_still_counts(
    tmp_path: Path,
) -> None:
    """Guard 2 must not red on contamination it is supposed to strip.

    The twin of the plant above (ADR-0022/R2 — a guard placed on one path is
    placed on its twin): if comment stripping regressed, this card would be
    reported as unestimated and the real defect would be hidden behind a
    false positive.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-337.md",))
    _replace_field(
        cards_dir / "CARD-337.md",
        "Estimate",
        "1c (0.5d) <!-- RE-ESTIMATED at the re-cut; board.md still says 2c -->",
    )
    cards = read_card_tree(cards_dir)
    assert "<!--" in cards[0].raw_estimate, "the plant must survive the raw parse"
    assert estimate_cycles(cards[0].raw_estimate) == 1.0
    assert waves_without_a_cycle_estimate(cards) == []


# --------------------------------------------------------------------------
# AC-3 — the three historical populations, each declared and asserted
# --------------------------------------------------------------------------


def test_the_scored_population_is_the_one_the_guards_speak_about(
    tree: tuple[Card, ...],
) -> None:
    """The denominator every AC-3 figure below is a share of.

    **231**, not CARD-363's 281. The difference is 50 ``done`` cards whose
    ``Review score`` holds a prose sentinel rather than a score, and they are
    counted here separately so the gap is visible rather than argued.
    """
    done = [c for c in tree if c.status == "done"]
    scored = scored_cards(tree)
    sentinel = [c for c in done if not c.is_scored]
    assert len(done) == 291, len(done)
    assert len(scored) == 231, len(scored)
    assert len(sentinel) == 60, len(sentinel)
    assert len(scored) + len(sentinel) == len(done)
    # and no sentinel card smuggles a score in behind a comment
    assert all(not _SCORE_VALUE.search(c.raw_score) for c in sentinel)


def test_declared_bound_the_cards_carrying_no_review_cycle_marker(
    tree: tuple[Card, ...],
) -> None:
    """AC-3, population 1 — **128** scored cards carry no marker at all.

    Declared, not fixed. G-2: writing markers onto them would invent
    intermediate scores nobody recorded, so the honest record is the count.
    The residue assertion is what makes this a bound and not an excuse — the
    population must be **entirely** behind the forward boundary, because a
    single in-scope member would mean guard 1 is being quietly weakened.
    """
    population = by_class(tree)[NO_MARKER]
    assert len(population) == 128, (
        f"{len(population)} scored cards carry no '[Review N/M] Score:' "
        "marker; the declared bound is 128. Re-derive before editing this "
        f"number. Difference: {sorted(set(population))[:5]}"
    )
    in_scope = [
        name
        for name in population
        if (w := next(c.wave for c in tree if c.name == name)) is not None
        and w >= ESTIMATE_UNIT_FIRST_WAVE
    ]
    assert in_scope == [], (
        "a card at or after wave "
        f"{ESTIMATE_UNIT_FIRST_WAVE} carries no marker: {in_scope}"
    )


def test_declared_bound_the_cards_whose_marker_disagrees_with_the_score(
    tree: tuple[Card, ...],
) -> None:
    """AC-3, population 2 — **50** scored cards disagree with themselves.

    Each carries at least one marker and a score naming a different cycle, so
    the retrospective's ``cycles_used`` and the card's own prose cannot both
    be right. CARD-363 reports 136 here; measured, it is 50, and the gap is
    the same denominator and the same narrow cycle regex as everywhere else.
    """
    population = by_class(tree)[MARKER_DISAGREES]
    assert len(population) == 50, (
        f"{len(population)} scored cards disagree; the declared bound is 50. "
        f"Re-derive before editing. Sample: {sorted(population)[:5]}"
    )
    assert marker_disagreements(tree) == [], "none of them may be in scope"


def test_declared_bound_the_cards_whose_score_names_no_cycle(
    tree: tuple[Card, ...],
) -> None:
    """AC-3, population 3 — **3** cards, named, and this is the one to get right.

    "The marker count equals the cycle the score names" is *undefined* for a
    card whose score names none. Excluding such cards silently is exactly the
    filter (``if named is not None``) that produced CARD-363's own wrong
    figure, so they are enumerated here by name.

    CARD-363 declares this population at **71**. Measured, it is **3** — and
    all three are a bare score with no cycle text of any kind (``9.5``,
    ``9.2``, ``9.5``). The 71 is the inflated denominator (281 against 231)
    plus a ``cycle N of M`` reading that misses the 169 cards writing
    ``cycle N/M``; see the module docstring.
    """
    population = by_class(tree)[SCORE_NAMES_NO_CYCLE]
    assert sorted(population) == ["CARD-029.md", "CARD-035.md", "CARD-066.md"], population
    # named for a reason: each really is a bare score, not a parse miss
    for name in population:
        card = next(c for c in tree if c.name == name)
        assert re.fullmatch(r"\d+\.\d+", strip_comments(card.raw_score)), card.raw_score
    in_scope = [
        name
        for name in population
        if (w := next(c.wave for c in tree if c.name == name)) is not None
        and w >= ESTIMATE_UNIT_FIRST_WAVE
    ]
    assert in_scope == [], in_scope


def test_declared_bound_the_waves_estimated_in_days_not_cycles(
    tree: tuple[Card, ...],
) -> None:
    """Guard 2's own historical bound — **244** cards, every one behind the line.

    This is the denominator gap the card is really about: 251 cards carry a
    numeric ``Wave`` and only 7 state an ``Nc`` estimate. All 7 are at or
    after wave :data:`ESTIMATE_UNIT_FIRST_WAVE`, and all 244 are before it —
    which is what identifies the boundary as the convention's start rather
    than an arbitrary cut.
    """
    waved = [c for c in tree if c.wave is not None]
    with_cycles = [c for c in waved if estimate_cycles(c.raw_estimate) is not None]
    without = [c for c in waved if estimate_cycles(c.raw_estimate) is None]
    assert len(waved) == 251, len(waved)
    assert len(with_cycles) == 7, [c.name for c in with_cycles]
    assert len(without) == 244, len(without)
    assert {c.wave for c in with_cycles} == {74, 75, 76}, [
        (c.name, c.wave) for c in with_cycles
    ]
    assert max(c.wave for c in without) < ESTIMATE_UNIT_FIRST_WAVE, [
        (c.name, c.wave) for c in without if c.wave >= ESTIMATE_UNIT_FIRST_WAVE
    ]


def test_declared_bound_markers_written_outside_the_worktree_notes(
    tree: tuple[Card, ...],
) -> None:
    """A fourth measured residue, beyond AC-3, and it is a live finding.

    **16** scored cards carry a ``[Review N/M] Score:`` marker somewhere other
    than ``## Worktree notes``, where the retrospective's extraction cannot
    see it. Five of them are recent (CARD-220, 269, 304, 306, 314): the
    extraction reads ``cycles_used = null`` for a card that does carry its
    marker. Declared here so the number cannot grow unremarked.
    """
    misplaced = []
    for card in scored_cards(tree):
        whole = sum(1 for line in card.text.splitlines() if _MARKER.match(line))
        in_notes = card.marker_count or 0
        if whole != in_notes:
            misplaced.append(card.name)
    assert len(misplaced) == 16, f"declared bound is 16, found {len(misplaced)}: {misplaced}"
    assert {"CARD-220.md", "CARD-269.md", "CARD-304.md", "CARD-306.md", "CARD-314.md"} <= set(
        misplaced
    ), misplaced


# --------------------------------------------------------------------------
# AC-4 — an unclassifiable card is a FAILURE, not a skip
# --------------------------------------------------------------------------


def test_every_scored_card_lands_in_exactly_one_class(tree: tuple[Card, ...]) -> None:
    """AC-4 — the walk partitions the population; nothing falls through.

    The partition identity is the real guard here: if a future spelling
    escapes every branch, the sum stops matching the population and this reds,
    rather than a card quietly vanishing from a mean.
    """
    buckets = by_class(tree)
    assert set(buckets) == set(CLASSES)
    assert sum(len(v) for v in buckets.values()) == len(scored_cards(tree)) == 231
    assert len(buckets[AGREES]) == 50, len(buckets[AGREES])
    assert buckets[UNCLASSIFIABLE] == (), buckets[UNCLASSIFIABLE]
    # every scored card names a cycle or is one of the three declared
    named = len(scored_cards(tree)) - len(buckets[SCORE_NAMES_NO_CYCLE])
    assert named == 228, named


def test_an_unclassifiable_card_is_a_failure_and_not_a_skip(tmp_path: Path) -> None:
    """AC-4's control: a scored card with no ``## Worktree notes`` section.

    Its marker count is neither zero nor a number — "no record" and "a record
    saying zero" are different facts, and the retrospective folds the second
    into a mean. ADR-0039/R2 makes the shape a refusal, so the walk reports it
    and the partition assertion above fails. It is never passed over.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-337.md",))
    control = read_card_tree(cards_dir)
    assert unclassifiable_cards(control) == [], "the unplanted copy must be green"
    assert control[0].classification == AGREES

    planted = cards_dir / "CARD-337.md"
    planted.write_text(
        planted.read_text(encoding="utf-8").replace("## Worktree notes", "## Notes"),
        encoding="utf-8",
    )
    cards = read_card_tree(cards_dir)
    assert cards[0].marker_count is None
    assert cards[0].classification == UNCLASSIFIABLE
    found = unclassifiable_cards(cards)
    assert len(found) == 1 and found[0].startswith("CARD-337.md:"), found

    # and the partition no longer holds, which is what makes it a FAILURE
    buckets = by_class(cards)
    assert len(buckets[UNCLASSIFIABLE]) == 1
    assert buckets[AGREES] == ()


# --------------------------------------------------------------------------
# AC-5 — tracked files only
# --------------------------------------------------------------------------


def test_the_guards_read_only_tracked_files(tree: tuple[Card, ...]) -> None:
    """AC-5, verified two ways: dynamically and statically.

    Dynamic — every file :func:`read_card_tree` actually opened is in
    ``git ls-files``. Static — no string literal in this module's executable
    code names ``meta/review``, so nothing can reach the review YAMLs on a
    path this test's dynamic half does not walk.
    """
    tracked = _tracked_paths()
    assert tracked, "git ls-files returned nothing; the dynamic half is vacuous"
    read = [c.path.relative_to(REPO_ROOT).as_posix() for c in tree]
    assert read, "no card was read; the assertion below would be vacuous"
    assert [p for p in read if p not in tracked] == []
    assert all(p.startswith("meta/kanban/cards/") for p in read), read

    module = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(module)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    code_strings = [
        node.value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]
    assert code_strings, "the static half found no code strings at all"
    # The needles are assembled at runtime rather than written as literals,
    # because a static check written the obvious way is an inspection that
    # sees itself: its own `"meta/review"` literal is a code string in the
    # module it walks, and the assertion fails on nothing but itself. Measured
    # — that is exactly how this test first red.
    needles = ("meta" + "/" + "review", "/" + "review" + "/")
    assert [s for s in code_strings if any(n in s for n in needles)] == []


def test_the_estimate_unit_decision_still_has_no_adr_file() -> None:
    """The dangling ref, pinned — and this reds the day someone writes it.

    ``ADR-0055`` is cited by five board artefacts and resolves to no file:
    ``meta/architecture/decisions/adr/`` tops out at 0042. That is why
    :data:`ESTIMATE_UNIT_FIRST_WAVE` is named after the measured convention.
    This assertion is the measured residue of that finding (ADR-0039/R3); when
    the ADR is written, it fails here and points its author at the constant.
    """
    adr_dir = REPO_ROOT / "meta" / "architecture" / "decisions" / "adr"
    numbers = sorted(int(p.name[:4]) for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert numbers, adr_dir
    assert max(numbers) == 42, numbers
    assert 55 not in numbers, "ADR-0055 now exists; re-point ESTIMATE_UNIT_FIRST_WAVE"


# --------------------------------------------------------------------------
# The parsers, and the controls that show the choices are load-bearing
# --------------------------------------------------------------------------

#: Every cycle spelling measured on this board, with the cycle each names.
#: Built by hand from the real ``Review score`` values rather than generated,
#: so a parser change cannot move the expectation with it.
SCORE_CORPUS: tuple[tuple[str, int | None], ...] = (
    # the dominant spelling, 169 cards
    ("9.0 (cycle 2/3)", 2),
    ("9.5 (cycle 1/3)", 1),
    ("9.0 (cycle 3/3 — certified, no open Important)", 3),
    ("8.5 (cycle 2/3; 7.0 → 8.5, +1.5)", 2),
    ("9.0 (cycle 2/2)", 2),
    ("9.5 (cycle 3/3, redo) ✓ threshold reached, 0 critical/important", 3),
    # `cycle N of M`, 19 cards -- the only spelling CARD-363's premise read
    ("8.8 (cycle 1 of 3 — CERTIFIED)", 1),
    ("9.0 (cycle 3 of 3 — CERTIFIED; 7.0 → 8.5 → 9.0)", 3),
    # bare ordinal
    ("9.0 (cycle 1), all findings fixed", 1),
    ("9.0 (cycle 4, owner-granted)", 4),
    ("9.5/10 (cycle 3, final — ready to merge pending owner sign-off)", 3),
    # a count rather than an ordinal
    ("9.0 (2 cycles)", 2),
    ("9.5 (1 cycle + fix)", 1),
    ("8.5 (2 cycles)", 2),
    # the progression format: the FIRST number is not the score and the first
    # ordinal is not the cycle
    ("6.0 → 8.5 → **9.0 CERTIFIED** (cycle 3 of 3 — CERTIFIED)", 3),
    ("8.0 (c1) → 8.5 (c2) → 8.0 (c3/3) — min_score met every cycle", 3),
    ("7.5 (c1) → 7.8 (c2) → **8.5 (c3, PASS with 7 bounds)**", 3),
    ("8.0 (c1) → **7.5** (c2/3) — below min_score 8, trajectory DOWN", 2),
    # the decimal-point trap: "9.0 cycle" offers a bare `0` to a count regex
    ("7.0 → **9.0 cycle 2/3 CERTIFIED** (2 minor, neither gating)", 2),
    # the final cycle named FIRST, earlier ones after: `last` is wrong here
    ("8.0 (cycle 2; cycle 1 8.5)", 2),
    ("9.5 (cycle 2, CERTIFIED; cycle 1 was 6.0)", 2),
    ("8.5 (cycle 2 of 3, CERTIFIED; cycle 1 scored 7.0)", 2),
    ("7.0 (cycle 2, NOT CERTIFIED; cycle 1 was 6.0) — merged on a call", 2),
    # no cycle at all -- population 3
    ("9.5", None),
    ("9.2", None),
)


@pytest.mark.parametrize("text,expected", SCORE_CORPUS)
def test_cycle_named_reads_every_measured_score_spelling(
    text: str, expected: int | None
) -> None:
    """Both score formats, and the three others the tree actually uses."""
    assert cycle_named(text) == expected, text


def test_the_score_corpus_covers_the_spellings_it_claims_to() -> None:
    """The corpus cannot silently shrink past the shapes it exists to pin."""
    assert len(SCORE_CORPUS) >= 25, len(SCORE_CORPUS)
    assert sum(1 for t, _ in SCORE_CORPUS if "/" in t and "cycle" in t) >= 6
    assert sum(1 for t, _ in SCORE_CORPUS if " of " in t) >= 4
    assert sum(1 for t, _ in SCORE_CORPUS if "→" in t) >= 5
    assert sum(1 for t, e in SCORE_CORPUS if e is None) == 2


def test_the_decimal_score_does_not_leak_into_the_cycle() -> None:
    """The bug that cost a cycle, kept as a control that still fails.

    ``.`` is not a word character, so ``\\b(\\d+)\\s+cycles?\\b`` matches the
    ``0`` of ``9.0`` in ``9.0 cycle 2/3`` and — being leftmost — wins. The
    naive pattern is asserted to still read 0 here, so this test discriminates
    rather than merely agreeing with the fixed one.
    """
    text = "7.0 → **9.0 cycle 2/3 CERTIFIED** (2 minor, neither gating)"
    naive = _CYCLE_COUNT_NAIVE.search(text)
    assert naive is not None and int(naive.group(1)) == 0, text
    assert _CYCLE_COUNT.search(text) is None
    assert cycle_named(text) == 2


def test_cycle_named_beats_both_naive_readings_on_the_real_tree(
    tree: tuple[Card, ...],
) -> None:
    """The two wrong readings, counted on the board rather than argued.

    ``max`` is not a taste: ``first`` and ``last`` each disagree with it on a
    measured, non-empty set of real cards, and — measured, not predicted —
    those two sets are **disjoint**. 11 cards defeat ``first`` (the score
    field records a trajectory: ``8.0 (c1) → 8.5 (c2) → 8.0 (c3/3)``), a
    different 10 defeat ``last`` (the final cycle is named first and the
    earlier ones after: ``8.0 (cycle 2; cycle 1 8.5)``), and no card defeats
    both. So 21 of the 231 scored cards discriminate between the three
    readings, and neither naive one can be reached by narrowing the other.

    ``max`` over a free-text field is still a heuristic, and the last
    assertion is what keeps the guards from resting on it: none of the 21 is
    inside guard 1's forward scope. Every card the heuristic could be wrong
    about is in a declared historical bound, not in a live assertion.
    """
    first_wrong, last_wrong, n_of_m_blind = [], [], []
    for card in scored_cards(tree):
        score = strip_comments(card.raw_score)
        ordinals = cycle_ordinals(score)
        if not ordinals:
            continue
        correct = max(ordinals)
        if ordinals[0] != correct:
            first_wrong.append(card.name)
        if ordinals[-1] != correct:
            last_wrong.append(card.name)
        if _CYCLE_N_OF_M_ONLY.search(score) is None:
            n_of_m_blind.append(card.name)

    assert len(first_wrong) == 11, f"first-ordinal reading is wrong on {first_wrong}"
    assert len(last_wrong) == 10, f"last-ordinal reading is wrong on {last_wrong}"
    assert set(first_wrong).isdisjoint(last_wrong), (
        "the two naive readings now share a counterexample, so one of them "
        f"could be reached by narrowing the other: {set(first_wrong) & set(last_wrong)}"
    )
    # the spelling CARD-363's premise was measured with is blind to 209 of 231
    assert len(n_of_m_blind) == 209, (
        f"`cycle N of M` alone cannot read {len(n_of_m_blind)} of the "
        f"{len(scored_cards(tree))} scored cards; declared bound is 209"
    )
    # no card the heuristic could be wrong about is in guard 1's scope
    ambiguous = set(first_wrong) | set(last_wrong)
    in_scope = [
        c.name for c in ran_in_a_wave(tree, ESTIMATE_UNIT_FIRST_WAVE) if c.name in ambiguous
    ]
    assert in_scope == [], (
        "a card whose cycle ordinals are written out of order is inside "
        f"guard 1's scope, so the guard now rests on the heuristic: {in_scope}"
    )


def test_the_marker_regex_is_the_quantity_the_retrospective_counts() -> None:
    """``cycles_used`` counts Score lines, not every ``[Review N/`` prefix.

    The same cycle writes a Step 8h line and sometimes a family-check line
    under that prefix, so a prefix count over-attributes by 2-4x. A bullet in
    front of the bracket is tolerated; a marker that drops or displaces the
    ``/M`` denominator is not matched, which is the extraction's own disclosed
    data-quality gap rather than something widened here.
    """
    assert _MARKER.match("[Review 2/3] Score: 8.5 — CERTIFIED")
    assert _MARKER.match("- [Review 1/3] Score: 7.0")
    assert _MARKER.match("  * [Review 1/3] Score: 7.0")
    assert not _MARKER.match("[Review 2/3] Step 8h: suite green")
    assert not _MARKER.match("[Review 2/3] Family regression check: clean")
    assert not _MARKER.match("[Review 2] Score: 8.0")  # no /M
    assert not _MARKER.match("[Review 7/7 — grace] Score: 8.0")  # suffix inside
    assert not _MARKER.match("the [Review 1/3] Score: line was written late")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2c (1d)", 2.0),
        ("1c (0.25d)", 1.0),
        ("0.5d", None),
        ("1d", None),
        ("0.75d  <!-- was 0.25d; raised by the CARD-264 fold -->", None),
        ("2c (1d) <!-- RE-OPENED on a second measured harm -->", 2.0),
        ("—", None),
        ("1.5c (0.5d)", 1.5),
    ],
)
def test_estimate_cycles_reads_the_nc_term(value: str, expected: float | None) -> None:
    """Including the two shapes the comment trap produces."""
    assert estimate_cycles(value) == expected, value


@pytest.mark.parametrize(
    "value,expected",
    [
        ("76", 76),
        ("—", None),
        ("unscheduled", None),
        ("48 (started mid-wave on owner instruction)", 48),
        ("68 <!-- STAMPED 2026-10-30: owner sequenced this AFTER CARD-304. -->", 68),
    ],
)
def test_card_wave_reads_every_measured_wave_spelling(
    value: str, expected: int | None
) -> None:
    """All five shapes the ``Wave`` field is written in on this tree."""
    assert card_wave(value) == expected, value


# --------------------------------------------------------------------------
# The inline-comment trap, asserted on the RAW value
# --------------------------------------------------------------------------


def test_an_inline_comment_contaminates_the_raw_field_value(
    tree: tuple[Card, ...],
) -> None:
    """Asserted on the RAW value, because stripping first hides the subject.

    A check that cleans a value before looking at it cannot see that the value
    needed cleaning. So this test reads :attr:`Card.raw_estimate` and
    :attr:`Card.raw_wave` exactly as the real parser returns them, and asserts
    both that the comment is there and that an equality test against the
    intended value **fails** on it.

    CARD-363 states "two cards carry an inline comment on a parsed field
    today". Measured: **7** on ``Estimate`` and **15** on ``Wave``.
    """
    est = sorted(c.name for c in tree if "<!--" in c.raw_estimate)
    wave = sorted(c.name for c in tree if "<!--" in c.raw_wave)
    assert len(est) == 7, f"declared bound is 7, found {len(est)}: {est}"
    assert len(wave) == 15, f"declared bound is 15, found {len(wave)}: {wave}"

    for card in (c for c in tree if c.name in est):
        raw, clean = card.raw_estimate, strip_comments(card.raw_estimate)
        assert raw != clean, card.name
        assert raw.endswith("-->"), card.name
        # the point of asserting raw: an equality test on it is simply wrong
        assert raw != clean and clean == strip_comments(raw)

    for card in (c for c in tree if c.name in wave):
        assert not re.fullmatch(r"\d+", card.raw_wave), card.name
        assert card.wave is not None, card.name


def test_the_wave_and_estimate_readings_strip_comments_first(
    tree: tuple[Card, ...],
) -> None:
    """The other half: every contaminated value is still interpretable.

    Without stripping, 15 cards would read as unscheduled and drop out of
    guard 2's population entirely — a guard shrinking its own set is the
    failure mode ADR-0039/R1 names, and it would be silent.
    """
    contaminated = [c for c in tree if "<!--" in c.raw_wave]
    assert contaminated, "vacuous: no contaminated Wave field on the tree"
    assert all(_LEADING_WAVE.match(c.raw_wave) is None for c in contaminated) is False
    naive = [c.name for c in contaminated if not re.fullmatch(r"\d+", c.raw_wave)]
    assert len(naive) == len(contaminated), naive
    assert all(c.wave is not None for c in contaminated)

    in_scope_but_contaminated = [
        c.name
        for c in contaminated
        if c.wave is not None and c.wave >= ESTIMATE_UNIT_FIRST_WAVE
    ]
    # none today; the assertion exists so the twin above cannot go vacuous
    assert in_scope_but_contaminated == [], in_scope_but_contaminated


def test_parse_card_fields_reads_the_header_block_and_last_write_wins() -> None:
    """The reimplemented parse, on the two properties that matter."""
    text = (
        "# CARD-999: a card\n\n"
        "**Status:** done\n"
        "**Estimate:** 1c (0.5d)\n"
        "**Estimate:** 2c (1d)\n"
        "\n## Architecture context\n\n"
        "**Status:** this line is prose, not a field\n"
    )
    fields = parse_card_fields(text)
    assert fields["Estimate"] == "2c (1d)"
    assert fields["Status"] == "done"
    assert "\n## " not in header_block(text)
