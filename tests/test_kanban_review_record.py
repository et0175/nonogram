"""CARD-363 — the two inputs of the retrospective's cycle ratio, guarded.

``forge:retrospective``'s ``accuracy_ratio`` is ``cycles_used /
estimate_cycles`` (``forge_1``'s ADR-0055 — upstream's decision, not this
board's; see "The ADR is upstream's, and this repository's series does not hold
it" below). Both terms are read out of a card file, and until this module
existed neither was checked:

**The numerator.** ``cycles_used`` is the COUNT of ``[Review N/M] Score:``
lines in a card's ``## Worktree notes``. Nothing writes that marker reliably
and nothing ever compared it against the cycle the card's own ``Review score``
field names. Measured here on the whole card tree: of 231 ``done`` cards
carrying a numeric score, **128 carry no marker at all** and **50 carry a
number that disagrees** with the cycle their score states. The marker is the
weaker record of the two — and it is the only one the extractor reads.

**Why the 50 disagree, measured — and it is NOT that the cards are wrong.**
This module first described them as cards that "disagree with themselves, so
the retrospective's ``cycles_used`` and the card's own prose cannot both be
right". That reading is refuted by the cards. 49 of the 50 carry a marker
count *greater* than the cycle their score names, and the cause is upstream's
counting rule: ``cmd-review-cycle``'s sync point writes a ``Score`` line at
each of its **three** write sites, so a cycle that reaches its threshold emits
**two**. Counting distinct ``[Review N/M]`` **ordinals** instead of Score
*lines* takes the 50 down to **2** — CARD-192 and CARD-262 — with **zero**
regressions among the 50 cards that currently agree. 49 cards carry a
duplicated ordinal and they are one bounded era, **CARD-113 through
CARD-192, with nothing after it**. So the cards are fine and the rule is
wrong.

This module nonetheless **keeps counting what the extractor counts**, because
that count is the input it exists to guard: a guard that reads the field
better than its subject does stops reporting its subject's defect. The
measured correction is the finding handed upstream (G-3), alongside "read the
score field instead" and "five recent cards write their markers under a later
heading where the extraction cannot see them" — not an edit to ``forge_1``,
which is read-only. The measurement is carded as CARD-369.

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

The ADR is upstream's, and this repository's series does not hold it
===================================================================
**RETRACTED, not edited away.** An earlier version of this section was headed
"The decision has no ADR file" and said "**There is no such file**". That is
false. The file exists — ``forge_1``'s
``forge/meta/architecture/decisions/adr/0055-estimate-in-review-cycles.md``,
status *accepted*, dated 2026-09-05, titled for exactly this decision (the
estimate unit is expected review cycles, not days). Verified read-only; that
tree is not editable from here.

What is true is the narrower claim
:func:`test_the_estimate_unit_decision_still_has_no_adr_file` actually
measures: the ADR is **upstream's**, and *this* repository's series tops out at
``0042``, so a bare ``ADR-0055`` ref resolves to nothing here. It is cited that
way by ``meta/kanban/board.md``, ``meta/kanban/dispatcher.state``,
``meta/kanban/retro.md``, CARD-363, CARD-366 and CARD-367 — and CARD-367 is
where the cross-repository category error is recorded and owned. The forward
boundary below is named after the measured convention for that reason.

**The old pin's trigger was void and the pin is restated.** It promised to "red
the day someone writes it"; the ADR was already written, and dated
2026-09-05 — before the pin was. This board will never number a *local* ADR
0055 for an upstream decision, so that assertion was green and would have
stayed green forever. What CAN fire is the collision: if this repository's own
series ever reaches 0055, six artefacts silently start resolving a ref about
estimate units to a local ADR about something else. That is what is pinned,
and the series head is declared as a floor so that writing an unrelated
ADR-0043 — a correct board operation — does not red it. The function name is
left alone deliberately: CARD-367's AC-4 names it and owns its update.

Two parsing traps, both measured on this tree
=============================================
**1. A field value can carry an inline HTML comment.** The card format's field
parse (reimplemented in :func:`parse_card_fields`; see "Why reimplemented")
strips none, so ``**Estimate:** 2c (1d) <!-- … -->`` parses as the whole
string including the comment. Measured: **7** cards carry a comment inside
``Estimate`` and **15** inside ``Wave`` on the merge-base tree, **16** on
main's tip. **Both censuses are floors, because the board writes both comments
as correct operations** — a wave open and a re-stamp annotate ``Wave``, a
re-cut annotates ``Estimate`` — and an equality on either reds the suite for a
board doing the right thing. The 16th ``Wave`` comment is this module's own
card, re-stamped ``76`` → ``77`` when wave 76 closed around it.
Interpreting a field therefore means stripping comments first — and *checking*
for contamination means asserting on the RAW value, because a check that strips
before looking cannot see what it is looking for. Both halves are asserted:
:func:`test_an_inline_comment_contaminates_the_raw_field_value` reads raw,
:func:`test_the_wave_and_estimate_readings_strip_comments_first` reads stripped.

**And the stripping is INERT on this tree today — measured, and the claim it
replaces was false.** This module used to say that "without stripping, 15 cards
would read as unscheduled and drop out of guard 2's population entirely". They
would not. Both wave patterns are anchored ``^(\\d+)\\b``, so ``68 <!-- … -->``
reads **68** with the comment still in it. Re-derived with the module's own
regexes: stripping changes **0 of 372** ``Wave`` readings, **0 of 372**
``Estimate`` readings and **0 of 372** ``Review score`` cycle readings on
main's tree (0 of 365 on this branch's older copy of it). The code is still
right and still defensive — ``Estimate: 0.5d <!-- re-estimated from 2c -->``
really would be misread without it, and
:func:`test_comment_stripping_discriminates_on_the_shape_the_tree_lacks` is the
one control in this module that actually separates the two readings, because no
value on the real tree does. The claim of *present* necessity was the thing
that was wrong, and no number here is asserted against the tree: an assertion
that stripping changes nothing would itself red the day a card correctly gained
a comment that mentions an ``Nc`` term.

**2. The score field has at least five cycle spellings, and neither the first
nor the last number in it is the answer.** Measured frequencies over the 231
scored cards of the merge-base tree (232 and 170 on main's tip): ``cycle N/M``
dominates (169), ``cycle N of M`` is rare (19), and there are also bare
``cycle N``, ``cN`` / ``cN/M``, and ``N cycles`` (16) forms.

**The ``cN`` census is three different numbers and the figure has to say which
one it is.** ``4`` by this module's own :data:`_CYCLE_ORDINAL`; ``5`` if the
trailing ``\\b`` is dropped, which lets CARD-026's score text match on the
commit sha ``c08fe50``; ``6`` if the ``(?<![\\w.])`` lookbehind is dropped as
well, which adds CARD-219. All three are right about different regexes and
this module asserts none of them — the ``\\b`` is what keeps the sha out of
:func:`cycle_ordinals`, and :func:`test_the_decimal_score_does_not_leak_into_the_cycle`
is the control on the lookbehind. A bare "the ``cN`` count is N" is the shape
of claim this module exists to refuse.

Two independent ways to get the cycle wrong, both measured here rather than
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

Which figures move on a correct board operation, and which do not
=================================================================
**One rule, applied to every assertion in this module rather than to the cells
a reviewer happened to name.** For each one: *can a correct board operation
move this value?* **Yes** → a floor, or a subset or one-sided check, with the
measured figure kept in the message so the bound is still declared
(ADR-0039/R3). **No** → an equality, and the reason it cannot move is written
down beside it.

Three rounds each answered that question only for the cells the previous round
had listed, and each fix was correct and incomplete. The list this round works
from is instead the **five correct board operations** themselves, each
simulated against a copy of the card tree with the module required to stay
green:

1. **a card closure** — ``Status`` → ``done``, a ``Review score``, a
   ``[Review N/M] Score:`` marker. Moves ``done``, ``scored``, :data:`AGREES`
   and the spelling censuses. All floors.
2. **a wave open** — a ``Wave:`` stamp on a ready card, *with the dispatch
   comment*, which is this board's convention. Moves ``len(waved)``,
   ``len(with_cycles)``, the wave set, and the ``Wave``-comment census.
3. **a re-stamp** of an existing ``Wave:`` value. This is what wave 76's close
   did to *this module's own card*: ``76`` → ``77 <!-- RE-STAMPED … -->``.
4. **a re-estimate** — an inline comment on ``Estimate``, which the board
   writes as a matter of course (CARD-322's was written on 2026-10-31). Moves
   the ``Estimate``-comment census.
5. **a re-cut** — a card's ``Touches``/``Estimate`` changing, and a new card
   file appearing. Moves the total card count and nothing this module asserts.

Measured: all five, run as eight variants on a **git-initialised** copy of
main's cards (a copy without a repository around it reds the tracked-files test
spuriously; initialising one removes it), leave this module green. The same
eight against the previous version of this module red — the wave open of a
pre-74 ready card with an **additional** failure nobody had listed, which is
how ``len(without)`` became a ceiling.

**The asymmetry that survived three cycles, and what it cost.** This round
declined to assert an inertness *count* for comment-stripping, on the correct
ground that the board annotates re-estimates inline and such an equality would
red on a correct write — and never applied that reasoning one field over, to
the comment counts themselves. ``len(wave) == 15`` and the in-scope ban under
it were therefore still equalities when operations 2 and 3 landed on main, and
**both red on main's tip while 67 of 67 passed on the branch** (see below).
Both are one-sided now.

Measured across a real closure, for the record: CARD-348 closed on main between
two readings of the same cells and **five figures moved** — ``done`` 291→292,
``scored`` 231→232, :data:`AGREES` 50→51, the ``cycle N of M``-blind count
209→210, the ``cycle N/M`` census 169→170. ``Wave`` comments 15→16 and the
in-scope-contaminated set ``[]``→``['CARD-363.md']`` moved on operation 3, not
on a closure, which is why a rule stated over closures alone missed them. The
cells that are equalities today held identical across both: sentinel 60,
no-marker 128, disagreeing 50, naming-no-cycle 3 by name, historical total 181,
``without`` 244, misplaced 16, first-wrong 11, last-wrong 10, readable 19.

Why this module's own branch suite cannot gate it (INV-023)
===========================================================
INV-023 freezes ``meta/kanban/**`` on a card branch at the merge base, so the
tree reader run from this branch's worktree reads cards that **predate every
board write since the cut**. Measured, same commit, same module: **67 passed on
the branch, 2 failed / 65 passed against main's card tree.** That is how two
green review cycles coexisted with a module that would have red main on merge.
Every figure in this module is therefore derived against **main's** cards, and
there is one consequence for the floors: a floor must be satisfied on the
lowest tree the module can be run from, which is the merge base. So where the
two trees disagree the floor carries the **merge-base** figure and the message
names main's alongside it — ``>= 15`` with 16 named, not ``>= 16``, which would
red on the branch for no board reason at all.

The figures asserted below are this module's own measurements. **Re-derive
them; never paste a failure's printed number back in** — that is how this
board's censuses rot.
"""

from __future__ import annotations

import ast
import builtins
import io
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
#: measured convention rather than after ``ADR-0055``, which is ``forge_1``'s
#: decision and has no file in THIS repository's series — see the docstring.
ESTIMATE_UNIT_FIRST_WAVE = 74

# --------------------------------------------------------------------------
# Field and body parsing
# --------------------------------------------------------------------------

_FIELD_LINE = re.compile(r"^\*\*([A-Za-z][A-Za-z ]*):\*\*\s*(.*)$")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

#: The marker ``cmd-review-cycle`` writes at each of its **three** Score write
#: sites, so a cycle that reaches its threshold emits **two** — see the module
#: docstring, which measured that and names the three sites. It is the one
#: quantity ``cycles_used`` counts. A leading list bullet is tolerated (older
#: cards bullet their notes); a marker that drops or displaces the ``/M``
#: denominator is not matched, which is the retrospective extraction's own
#: disclosed rule, restated here rather than widened.
#:
#: **RETRACTED:** this comment used to call it "the ONE marker … writes once per
#: completed review cycle", forty lines under a docstring that had measured the
#: opposite and was right. The stale half is retracted here rather than quietly
#: replaced, because two live contradictory sentences in one file is the defect
#: this module exists to catch on cards.
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

#: An ``Nc`` term in ``Estimate``: ``2c (1d)``, ``1c (0.25d)``. Presence only —
#: :func:`estimate_cycles` is what rejects a term of **zero**, because the regex
#: matching ``0c`` is how ``0c`` used to pass guard 2.
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

    ``None`` is not ``0``, and the distinction is **this module's own**, not an
    inherited claim about what the retrospective does with each. A card with
    no notes section has nowhere for a marker count to be read *from* — the
    record is unreadable. A card with a notes section holding no marker is
    readable and says zero. Those are different defects with different fixes
    (write the section; write the marker), so this module classifies the first
    :data:`UNCLASSIFIABLE` and the second :data:`NO_MARKER` instead of
    collapsing them.

    **It is not justified by the retrospective's arithmetic, which does
    collapse them.** Upstream maps both shapes to one null — ``cycles_used``
    is null when a card carries no ``[Review N/M] Score:`` line *at all* —
    and a card with a null count is *skipped* from every mean, sum and ratio
    that reads it, "never folded in as 0". An earlier draft of this docstring
    said the retrospective "folds the second into a mean"; the upstream spec
    denies that twice. The distinction below is kept on its own merits.
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

    **``max`` has a THIRD failure mode, and it is disclosed rather than
    handled.** Upstream's per-invocation counter ``for cycle in
    1..max_cycles`` restarts at 1 on every manual ``/kanban review``
    re-entry, so a card reviewed across two invocations has a true cycle count
    equal to the *sum* of its Score lines, which ``max`` under-reads — the
    same reason upstream rejects "the N of the last Score line". Upstream's
    own case is CARD-091: six invocations of lengths 5/3/3/5/3/1, each
    restarting at ``1/6``, 20 true Score lines, where ``max`` reads 5 and
    "last" reads 1. Guard 1 compares the marker count (which sums across
    invocations) against this reading, so on a re-entered card it would red a
    **correct** record.

    Not handled, and the reason is the module's standing one: detecting a
    re-entry means reading the marker ordinals as something other than what
    the extractor counts, and no card this guard speaks about is re-entered,
    so the handling would be code with no case. Not live is *measured* rather
    than recalled —
    :func:`test_the_marker_count_agrees_with_the_cycle_the_score_names`
    asserts that no in-scope card's marker ordinals restart, so the day one
    does, that assertion reds and sends its author here instead of leaving
    guard 1 to red on a card that did nothing wrong.
    """
    ordinals = cycle_ordinals(score)
    return max(ordinals) if ordinals else None


def estimate_cycles(estimate: str) -> float | None:
    """The ``Nc`` term of an ``Estimate``, comments stripped, or ``None``.

    **A term of zero is ``None``, and that is a fix, not a convenience.**
    Guard 2's own violation message says ``accuracy_ratio`` "has no
    denominator", and a zero denominator *is* no denominator — the ratio is
    undefined, exactly as it is when the term is absent. Measured before the
    fix: planting ``0c (0.5d)`` on an in-scope card left every test in this
    module green while the matched control ``0.5d`` on the same card red guard
    2, because the regex asked only that an ``Nc`` term be *present*.
    :func:`test_a_planted_zero_cycle_estimate_reds_by_name` is the control.
    """
    match = _ESTIMATE_CYCLES.search(strip_comments(estimate))
    if match is None:
        return None
    cycles = float(match.group(1))
    return cycles if cycles > 0 else None


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
    """Guard 2 — a card that ran in a wave carries a *positive* cycle estimate.

    The two refusals are reported apart, because their remedies differ: a
    day-only estimate has to be re-priced in the unit, while ``0c`` is a term
    that is present and still unusable (see :func:`estimate_cycles`).
    """
    violations = []
    for card in ran_in_a_wave(cards, first_wave):
        if estimate_cycles(card.raw_estimate) is None:
            clean = strip_comments(card.raw_estimate)
            zero = _ESTIMATE_CYCLES.search(clean)
            fault = (
                f"states {zero.group(1)}c, a ZERO cycle estimate"
                if zero
                else "states no 'Nc' term"
            )
            violations.append(
                f"{card.name}: ran in wave {card.wave} with "
                f"Estimate {clean!r}, which {fault} — accuracy_ratio has no "
                "denominator"
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

    **Every equality a plant test asserts about a fixture card is a fixture
    PRECONDITION, and that is why they are equalities.** ``CARD-339.md``
    carries two markers and scores *cycle 2 of 3*; ``CARD-337.md`` carries one
    and ``1c (0.5d)``. Both are ``done``, closed and certified, so no correct
    board operation rewrites their score, markers or estimate — the one write a
    closed card still takes is a ``Wave`` re-stamp, which none of these
    assertions reads. Each is asserted with a message naming the fixture
    ("the fixture must carry exactly two markers") rather than the plant, so if
    a fixture card does change, the failure sends its reader to the fixture
    instead of to the arithmetic.
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

    The two pre-checks hold :func:`cycle_named`'s third disclosed failure mode
    to "not live": upstream's cycle counter restarts at 1 on a manual review
    re-entry, so a re-entered card's markers read ``1, 2, 3, 1, 2`` and its
    true count is the sum while ``max`` over the score field reads only the
    longest invocation. Every in-scope card is single-invocation today, which
    is **measured here** rather than asserted in a comment, so guard 1 cannot
    start resting on that without this reddening first.

    **Both pre-checks are order-free, and the stated reason for that is a
    measurement, not a preference** — see the comment below. Measured on main's
    tree after the fix: every in-scope card's ordinals are exactly ``1..max``
    with no repeat (``[1]`` four times, ``[1, 2]`` for CARD-339, ``[1]`` for
    CARD-348), and this card's own closure is green with its cycle-2 Score line
    written on *either* side of the cycle-1 line.

    **What an order-free comparison cannot do, disclosed.** It cannot tell
    upstream's threshold double-write from a true re-entry: both are a repeated
    ordinal, and position does not separate them either.

    **The figure for that last claim is restated, because as it stood it read
    as ten counterexamples where there is one.** It said "39 of the 49 cards
    carrying a duplicate duplicate the maximum and 10 duplicate below it",
    which is true only under one reading — 39 duplicate *only* the maximum and
    10 duplicate *something below* it — and invites the other, that 10 cards
    fail to duplicate the maximum. Re-derived on main's tree: **39 duplicate
    only the maximum, 9 duplicate the maximum and a value below it, and
    exactly 1 — CARD-192, ordinals ``1,1,2`` — duplicates below it without
    duplicating it.** So the maximum is among the duplicated values on **48 of
    49**, and the positional statistic has a single counterexample.

    **That restatement makes the figure weaker evidence, and the ruling does
    not rest on it.** 48 of 49 is close to a discriminator, and if this were
    the only argument the right move would be to try it. It is not. The
    separating fact between a double-write and a re-entry is the **invocation
    count**, and that is recorded nowhere a runtime can enumerate: three
    positional statistics over the 49 — which ordinal repeats, how often, and
    where in the section the repeat sits — are all satisfied *identically* by a
    re-entry of equal-length invocations (``1,2,3`` then ``1,2,3`` is
    indistinguishable from one invocation double-writing every cycle). A check
    cannot decide from evidence that cannot settle it, so the message names
    both causes with the measured dominant one first. The order-sensitive
    spelling *appeared* to separate them; what it read was where a human had
    typed a line.
    """
    in_scope = [
        c
        for c in ran_in_a_wave(tree, ESTIMATE_UNIT_FIRST_WAVE)
        if c.status == "done" and c.is_scored
    ]
    population = [c.name for c in in_scope]
    assert len(population) >= 5, (
        "guard 1 has gone vacuous: no card from wave "
        f"{ESTIMATE_UNIT_FIRST_WAVE} onwards is done-and-scored. Population: "
        f"{population}"
    )
    # BEFORE the guard, deliberately. A card whose ordinals are not a clean
    # 1..max reds the guard too -- marker count 4 against a score naming cycle
    # 2 -- but it reds it with a bare `marker_disagreements(tree) == []`, which
    # says the record is wrong when the record may be right. Measured: planting
    # a re-entry on CARD-339 (markers 1,2,1,2) reds the guard assertion with no
    # message at all. These checks run first so the explanation arrives instead
    # of the accusation.
    #
    # Compared ORDER-FREE. The first spelling of this check compared
    # CONSECUTIVE WRITTEN ordinals and refused on any non-increase, which made
    # its verdict depend on where in `## Worktree notes` a line was inserted:
    # measured on main's tree, closing THIS card with its `[Review 2/3] Score:`
    # line written ABOVE the cycle-1 line red, and the identical closure with
    # that line written BELOW was green, nothing but the position differing --
    # while this card's own notes are ordered newest-first. A guard whose
    # greenness depends on the insertion position of a note is not a guard on
    # the record. Neither shape it looks for needs the order: a re-entry and a
    # double-write are both a REPEATED ordinal, and a lost marker is a GAP.
    ordinals_by_card = {}
    for card in in_scope:
        section = worktree_notes(card.text) or ""
        ordinals_by_card[card.name] = [
            int(found.group(1))
            for line in section.splitlines()
            if (found := _MARKER.match(line))
        ]
    repeated = {
        name: found
        for name, found in ordinals_by_card.items()
        if len(found) != len(set(found))
    }
    gapped = {
        name: found
        for name, found in ordinals_by_card.items()
        if found and sorted(set(found)) != list(range(1, max(found) + 1))
    }
    # A repeated ordinal has TWO causes and the message used to name only the
    # rarer one. Upstream's threshold double-write is the board's measured
    # dominant cause: 49 scored cards carry a duplicated ordinal, and planted
    # in-scope ordinals 1,2,2 -- which is what upstream's own flow emits
    # unaided -- fired this check with "the signature of a manual review
    # re-entry" when no re-entry had occurred.
    assert repeated == {}, (
        "an in-scope card writes the same '[Review N/M]' ordinal twice, so its "
        "marker COUNT exceeds the cycles it ran and guard 1 below is about to "
        "call a possibly-correct record wrong. TWO causes, and they cannot be "
        "told apart from the ordinals alone — both are a repeated ordinal, and "
        "the duplicate's position does not separate them either: of the 49 "
        "scored cards on this board carrying one, 39 duplicate ONLY the "
        "maximum, 9 duplicate the maximum AND a value below it, and exactly "
        "ONE (CARD-192, ordinals 1,1,2) duplicates below it without "
        "duplicating it — so the maximum is among the duplicated values on 48 "
        "of the 49, and 'the duplicate is the last cycle' has a single "
        "counterexample, not ten. (1) UPSTREAM'S THRESHOLD DOUBLE-WRITE, the "
        "dominant cause here: cmd-review-cycle writes a Score line at each of "
        "three write sites, so a cycle that reaches its threshold emits two. "
        "The record is right, the counting rule is wrong, and the fix is "
        "upstream's (CARD-369) — meanwhile write a closing stamp "
        "single-ordinal. (2) A MANUAL REVIEW RE-ENTRY: upstream's counter "
        "restarts at 1 per invocation, so the true cycle count is the SUM of "
        "the Score lines while cycle_named's `max` over the score field reads "
        f"only the longest invocation — see its docstring. {repeated}"
    )
    assert gapped == {}, (
        "an in-scope card's '[Review N/M]' ordinals do not cover 1..max, so a "
        "cycle's Score marker is MISSING and the count under-reads the cycles "
        "the card ran — a different defect from a repeat, with a different "
        "remedy (write the missing marker). The historical instance is "
        "CARD-262, whose only ordinal is 3; it is out of scope. "
        f"{gapped}"
    )

    assert marker_disagreements(tree) == []


def test_a_planted_marker_disagreement_reds_by_name(tmp_path: Path) -> None:
    """AC-1's control: drop one marker from a real in-scope card.

    CARD-339 ran in wave 74, scores *cycle 2 of 3* and carries two markers.
    Deleting one makes the record claim a cycle it cannot evidence — exactly
    the shape the retrospective would read as ``cycles_used = 1``.

    **The restored marker is inserted after the notes HEADING, not appended at
    end of file**, and the count it produces is asserted rather than left to a
    substring. Appending was this round's own defect: CARD-339's
    ``## Worktree notes`` is followed by a later ``## Notes``, so an appended
    marker lands *outside* the section, the in-notes count is **0**, and the
    message reads ``0 … marker(s)``. The two assertions passed anyway because
    they only looked for the substrings ``marker(s)`` and ``cycle 2``. The
    archetypal AC-1 shape — ``0 < count != named``, which is what all 50
    historical members of population 2 look like — was then demonstrated by no
    plant at all. The `marker_count == 1` assertion below is what makes that
    unrepeatable.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-339.md", "CARD-337.md"))
    control = read_card_tree(cards_dir)
    assert marker_disagreements(control) == [], "the unplanted copy must be green"
    assert [c.marker_count for c in control if c.name == "CARD-339.md"] == [2]

    planted = cards_dir / "CARD-339.md"
    lines = planted.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if not _MARKER.match(line)]
    assert len(lines) - len(kept) == 2, "the fixture must carry exactly two markers"
    one_back = next(line for line in lines if _MARKER.match(line))
    heading = next(
        i for i, line in enumerate(kept) if _WORKTREE_NOTES_HEADING.match(line)
    )
    planted.write_text(
        "".join(kept[: heading + 1] + [one_back] + kept[heading + 1 :]),
        encoding="utf-8",
    )

    cards = read_card_tree(cards_dir)
    card = next(c for c in cards if c.name == "CARD-339.md")
    assert card.marker_count == 1, (
        "the restored marker must land INSIDE '## Worktree notes'; a count of "
        f"0 means it was appended past the later heading. Got {card.marker_count}"
    )
    assert card.cycle_named == 2, card.raw_score
    assert card.classification == MARKER_DISAGREES, card.classification

    found = marker_disagreements(cards)
    assert len(found) == 1, found
    assert found[0].startswith("CARD-339.md:"), found
    assert "1 '[Review N/M] Score:' marker(s)" in found[0], found
    assert "cycle 2" in found[0], found


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


def test_a_planted_in_scope_score_naming_no_cycle_reds_by_name(tmp_path: Path) -> None:
    """AC-1's **third** refusal arm, which had no dedicated control.

    Guard 1 refuses three shapes and two of them were demonstrated: a count
    that disagrees (:func:`test_a_planted_marker_disagreement_reds_by_name`)
    and a card with nowhere to read a count from
    (:func:`test_a_planted_card_with_no_notes_section_reds_by_name`). The
    third — an **in-scope** card whose ``Review score`` names no review cycle
    at all — was live code with no plant behind it, which is the ADR-0039/R1
    gap: a refusal nobody has watched fire.

    It is live, and measured: a bare ``9.0`` planted on in-scope CARD-348, on
    a copy of main's cards, reds **five** tests — guard 1, both bounds that
    speak about the class, the class partition, and the marker-agreement
    check. Guard 1 cannot compare a marker count against a cycle the score
    does not name, and *silently excluding* such a card is precisely the filter
    (``if named is not None``) that produced CARD-363's own wrong figure. The
    three cards in that class on the real tree are all behind the forward
    boundary and held by
    :func:`test_declared_bound_the_cards_whose_score_names_no_cycle`; this
    plants a fourth inside it.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-337.md", "CARD-339.md"))
    control = read_card_tree(cards_dir)
    assert marker_disagreements(control) == [], "the unplanted copy must be green"

    # a bare score, which is exactly the shape all three real members carry
    _replace_field(cards_dir / "CARD-337.md", "Review score", "9.0")
    cards = read_card_tree(cards_dir)
    card = next(c for c in cards if c.name == "CARD-337.md")
    assert card.is_scored, card.raw_score
    assert card.cycle_named is None, card.raw_score
    assert card.classification == SCORE_NAMES_NO_CYCLE, card.classification

    found = marker_disagreements(cards)
    assert len(found) == 1, found
    assert found[0].startswith("CARD-337.md:"), found
    assert "names no review cycle" in found[0], found
    # reported by the arm it belongs to, not as a count disagreement
    assert "marker(s)" not in found[0], found
    # and the card is NOT passed over: it lands in a declared class, and the
    # by-name declaration of that class reds on it
    assert sorted(by_class(cards)[SCORE_NAMES_NO_CYCLE]) == ["CARD-337.md"], by_class(
        cards
    )[SCORE_NAMES_NO_CYCLE]


# --------------------------------------------------------------------------
# AC-2 — a card that ran in a wave carries a cycle estimate
# --------------------------------------------------------------------------


def test_a_card_that_ran_in_a_wave_carries_a_cycle_estimate(
    tree: tuple[Card, ...],
) -> None:
    """AC-2 — guard 2 on the real tree, with the same anti-vacuity floor.

    The floor here and the bound in
    :func:`test_declared_bound_the_waves_estimated_in_days_not_cycles` speak
    about the same seven cards, and cycle 2 found this module asserting ``>= 7``
    here and ``== 7`` there. The equality was the wrong one of the two: this
    population gains a member at every wave open. Both are floors now.
    """
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


def test_a_planted_zero_cycle_estimate_reds_by_name(tmp_path: Path) -> None:
    """AC-2's third refusal arm: a term that is present and still unusable.

    ``0c`` is not a day-only estimate and not a missing one — it is an ``Nc``
    term that divides nothing. Measured before the fix, and this is why the arm
    exists: planting ``0c (0.5d)`` on CARD-337 left **every** test in this
    module green, while the matched control ``0.5d`` on the same card red guard
    2 in the same run. Guard 2's own message said ``accuracy_ratio`` "has no
    denominator" about the second and nothing at all about the first.
    """
    cards_dir = _copy_tree(tmp_path, ("CARD-337.md", "CARD-339.md"))
    assert waves_without_a_cycle_estimate(read_card_tree(cards_dir)) == []

    _replace_field(cards_dir / "CARD-337.md", "Estimate", "0c (0.5d)")
    cards = read_card_tree(cards_dir)
    card = next(c for c in cards if c.name == "CARD-337.md")
    assert "0c" in card.raw_estimate, "the plant must survive the raw parse"
    assert estimate_cycles(card.raw_estimate) is None, card.raw_estimate

    found = waves_without_a_cycle_estimate(cards)
    assert len(found) == 1, found
    assert found[0].startswith("CARD-337.md:"), found
    # reported by name as a zero, NOT as the absent term it is not
    assert "a ZERO cycle estimate" in found[0], found
    assert "no 'Nc' term" not in found[0], found
    assert "no denominator" in found[0], found


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

    **231**, not CARD-363's 281. The difference is **60** ``done`` cards whose
    ``Review score`` is not a score: 50 hold a prose sentinel (*"merged
    without a review cycle, at the owner's call"*) and 10 are a bare ``—``.
    They are counted here separately so the gap is visible rather than argued.

    **Both totals are FLOORS, and that is load-bearing.** ``done`` and
    ``scored`` each grow by one every time a card is correctly closed — this
    card's own merge gate moves them again — so an equality here would red the
    suite on main for doing the right thing. The floors carry this branch's
    reading of the tree; main's tip already reads 292/232, because CARD-348
    closed there. That closure is the live proof rather than a prediction: the
    pre-fix module, run against main's cards, reds three tests. The measured
    figures stay in the message, so the bound is still declared (ADR-0039/R3)
    and a
    *shrinking* population still reds.

    **``sentinel`` is a floor too, and the equality it replaces was the same
    mistake one field over.** It used to be argued as "a correctly reviewed
    closure does not land there, so a 61st owner's-call merge is exactly the
    event that should be remarked rather than absorbed". But an owner's-call
    merge is a **correct board operation** — 60 cards record one, the owner
    authorises it deliberately, and nothing this module guards is violated by
    it. A test that stops the suite because the owner merged a cost card on
    their own call is the board bending to the test, and the remedy it implies
    is editing this number, which is how a census rots. Disclosed loss
    (ADR-0039/R3): the 61st owner's-call merge no longer stops the board. What
    is kept is the measured figure in the message, the shrink detection, and
    the no-smuggled-score check below, which is what actually holds the
    ``scored``/``sentinel`` split apart.

    **The partition identity below is STRUCTURAL and is not what keeps the pair
    honest.** It used to be presented as "what keeps the pair honest under
    growth", which it cannot be: ``sentinel`` is *defined* two lines above it as
    ``done`` minus ``is_scored``, so ``scored + sentinel == done`` is true by
    construction and can never fail. The same shape this module flags plainly
    at the class partition was left unflagged here. What actually carries this
    test is the ``sentinel == 60`` equality and the no-smuggled-score check
    under it.
    """
    done = [c for c in tree if c.status == "done"]
    scored = scored_cards(tree)
    sentinel = [c for c in done if not c.is_scored]
    assert len(done) >= 291, f"{len(done)} done cards; the measured floor is 291"
    assert len(scored) >= 231, f"{len(scored)} scored cards; the measured floor is 231"
    assert len(sentinel) >= 60, (
        f"{len(sentinel)} done cards hold a prose sentinel instead of a score; "
        "the measured floor is 60 (50 a sentence, 10 a bare '—'), identical on "
        "both trees. A floor, because an owner's-call merge is a correct board "
        "operation and 60 cards record one. A SHRINK means a sentinel was "
        "replaced by a score, which moves a card into `scored` and into one of "
        "the three declared historical classes"
    )
    # structural, and said to be: `sentinel` is `done` minus `is_scored`, so
    # this cannot fail. Kept as documentation of the split, not as a control.
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

    **What a COUNT does not see, disclosed rather than fixed (ADR-0039/R3).**
    Every bound in this module except population 3 is a count, not a set, so a
    *compensating* move between two classes is invisible to all of them.
    Measured, on a copy of main's tree: CARD-002 loses both its true Score
    markers (``AGREES`` → ``NO_MARKER``) while CARD-005 gains one fabricated
    marker matching the cycle its score names (``NO_MARKER`` → ``AGREES``), and
    **every count is unchanged** — 128, 50, 3, 51 agreeing, 181 historical, 16
    misplaced — with all thirteen tree-tests green. One half of that plant is
    the history fabrication G-2 forbids. This is not a regression from making
    the growing cells floors: the absolutes those replaced would not have moved
    either. It is the standing limit of a count. Pinning the two large
    populations by name or by hash would be a bound nobody can maintain across
    a board whose populations move at every closure, so the limit is stated
    here instead: **these bounds detect that a population moved, never which
    cards moved inside it.** Population 3 is named member-by-member precisely
    because it is small enough to be, and it is the one cell that would catch
    such a swap if it touched those three cards.
    """
    population = by_class(tree)[NO_MARKER]
    assert len(population) == 128, (
        f"{len(population)} scored cards carry no '[Review N/M] Score:' "
        "marker; the declared bound is 128, identical on the merge-base tree "
        "and on main's tip. An EQUALITY, and the reason is written in this "
        "test's docstring: the only way into this class is a closure that "
        "writes no marker, which is the defect this module exists to guard, "
        "and a correct closure lands in AGREES instead. Re-derive before "
        "editing this number; the NEWEST members are where a new one appears: "
        f"{sorted(set(population))[-5:]}"
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
    """AC-3, population 2 — **50** scored cards whose marker count disagrees.

    Each carries at least one marker and a score naming a different cycle.
    CARD-363 reports 136 here; measured, it is 50, and the gap is the same
    denominator and the same narrow cycle regex as everywhere else.

    **The cards are not the defect; the counting rule is.** Measured: 49 of
    the 50 carry a count *greater* than the cycle their score names, because
    upstream's sync point writes a ``Score`` line at each of its three write
    sites and a threshold-reaching cycle therefore emits two. Counting
    distinct ``[Review N/M]`` ordinals instead of Score lines takes 50 to
    **2** (CARD-192, CARD-262) with **zero** regressions among the 50
    agreeing cards, and the 49 cards carrying a duplicated ordinal are one
    bounded era: **CARD-113 to CARD-192, nothing after it**. The earlier
    reading here — that these cards "disagree with themselves" and "cannot
    both be right" — was a cause asserted about a record rather than read off
    it, in a module whose subject is exactly that.

    This bound still counts Score *lines*, deliberately: that is the quantity
    the retrospective extracts, so it is the quantity worth guarding. The
    correction is a finding for upstream (CARD-369), not a change here.

    This is a count and not a set, with the consequence disclosed in
    :func:`test_declared_bound_the_cards_carrying_no_review_cycle_marker`: it
    sees that the population moved, never which cards moved inside it.
    """
    population = by_class(tree)[MARKER_DISAGREES]
    assert len(population) == 50, (
        f"{len(population)} scored cards disagree; the declared bound is 50, "
        "identical on the merge-base tree and on main's tip. An EQUALITY: the "
        "only way into this class is a closure whose marker count contradicts "
        "its own score, which is the defect this module exists to guard. "
        "Re-derive before editing; the NEWEST members are where a new one "
        f"appears: {sorted(population)[-5:]}"
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

    **Three of these cells grow at a WAVE OPEN, which is the second correct
    board operation this module red on.** ``waved`` and ``with_cycles`` gain a
    card every time one is stamped with a wave, and the wave *set* gains a
    member every time a wave opens. Measured before the fix: stamping
    ``Wave: 77`` on CARD-369 — a card whose estimate is already ``1c (0.5d)``,
    so the plant is the estimate convention *working* — red this test with the
    bare message ``252`` and no explanation at all, which is the same "a
    correct card accused with no reason" defect this round had just fixed
    elsewhere. CARD-367 through CARD-373 are cut and unwaved, so wave 77's open
    is the next board operation that touches this. So the two counts are now
    floors carrying their measured figures, and the wave set is a **subset**
    check.

    **``len(without)`` is a CEILING, not the equality it was, and the reason is
    a fourth board operation the round had not listed.** Growth is a defect —
    a card ran in a wave without a cycle estimate, which guard 2 itself reds,
    or a pre-74 card was re-stamped forward and not re-priced — so a ceiling
    keeps everything the equality was for. A **shrink**, though, is the
    convention working: re-stamping a pre-74 card's ``Wave`` forward *and*
    re-pricing it in cycles is what a wave open does to a card picked up out of
    the backlog, and it takes a member out of this set. CARD-310 is the live
    case — ``ready``, ``Wave: 67``, ``Estimate: 0.5d`` — and dispatching it
    correctly would have red the equality at 243. That is the same class of
    defect as the comment counts, found by asking the question of this cell
    rather than of the cells a reviewer had named.

    **``min(...) == 74`` stays an equality**, and the reason is that it asserts
    a *definition* rather than a census: :data:`ESTIMATE_UNIT_FIRST_WAVE` is
    *defined* as the wave where the convention starts, so the minimum moving
    means the constant is now wrong and the remedy is to re-derive it, not to
    edit a number. It is also what forbids a cycle estimate appearing *behind*
    the boundary, which is what keeps the boundary identified rather than
    assumed. ``max(...) < 74`` is one-sided already and holds the mirror.
    """
    waved = [c for c in tree if c.wave is not None]
    with_cycles = [c for c in waved if estimate_cycles(c.raw_estimate) is not None]
    without = [c for c in waved if estimate_cycles(c.raw_estimate) is None]
    assert len(waved) >= 251, (
        f"{len(waved)} cards carry a numeric Wave; the measured floor is 251. "
        "A floor, because a wave open adds to this. A SHRINK means a Wave "
        "stamp was removed or stopped parsing."
    )
    assert len(with_cycles) >= 7, (
        f"{len(with_cycles)} waved cards state an 'Nc' estimate; the measured "
        f"floor is 7. {[(c.name, c.wave) for c in with_cycles]}"
    )
    assert len(without) <= 244, (
        f"{len(without)} waved cards state no 'Nc' estimate; the measured "
        "ceiling is 244, identical on both trees. A CEILING, not an equality: "
        "growth means a card ran in a wave without a cycle estimate — which "
        "guard 2 itself reds — or a pre-74 card was re-stamped forward and not "
        "re-priced, while a SHRINK is the convention working. CARD-310 is the "
        "live case: ready, Wave 67, Estimate 0.5d, so dispatching it correctly "
        "re-stamps its wave and re-prices it in cycles, taking this to 243. An "
        "equality here would red on that, which is the same defect as the "
        f"comment counts. Members at or past the boundary: "
        f"{[(c.name, c.wave) for c in without if c.wave >= ESTIMATE_UNIT_FIRST_WAVE]}"
    )
    assert {74, 75, 76} <= {c.wave for c in with_cycles}, (
        "a wave that was measured to estimate in cycles no longer has a "
        f"cycle-estimated card: {sorted({c.wave for c in with_cycles})}"
    )
    assert min(c.wave for c in with_cycles) == ESTIMATE_UNIT_FIRST_WAVE, (
        "a cycle estimate appears BEHIND the forward boundary, so wave "
        f"{ESTIMATE_UNIT_FIRST_WAVE} is no longer where the convention starts: "
        f"{sorted((c.name, c.wave) for c in with_cycles)[:5]}"
    )
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
    assert len(misplaced) == 16, (
        f"declared bound is 16, found {len(misplaced)}. An EQUALITY: the only "
        "way into this set is a Score marker written outside '## Worktree "
        "notes', which is the defect this bound declares, not a correct board "
        "operation — a correct closure writes its markers inside the section, "
        "and CARD-363's own three are measured there. A SHRINK means a "
        f"misplaced marker was moved or removed. {misplaced}"
    )
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

    **The identity is stated against the live population and not against an
    absolute**, and the agreeing class is a floor, for the reason given in
    :func:`test_the_scored_population_is_the_one_the_guards_speak_about`: a
    correctly closed card adds one to ``scored`` and lands in
    :data:`AGREES`, so ``== 231`` and ``== 50`` would both red on main the
    moment this card merges. The identity loses nothing by dropping the
    absolute — it was never the absolute that caught an escaping spelling.

    The names-a-cycle count is stated as ``scored`` minus the **three**
    declared members of :data:`SCORE_NAMES_NO_CYCLE` rather than as 228. That
    is closure-invariant and still has teeth: a fourth card whose score names
    no cycle reds it, which is the whole point of population 3.

    **Where the teeth went, stated plainly.** The sum identity on its own is
    *structural*: :func:`by_class` buckets every scored card by construction,
    and an unknown class would ``KeyError`` rather than be dropped, so the sum
    can never differ. It was the ``== 231`` that made this the module's
    strongest assertion, and dropping the absolute without replacing it would
    have been a loosening dressed as a fix. The replacement is the
    **historical total**: the three declared classes sum to ``128 + 50 + 3 =
    181``, every one of them closure-invariant, because a correctly closed
    card lands in :data:`AGREES` and in none of them. That equality bites on
    exactly what the absolute used to bite on — any card moving between
    classes — and does not move when a card closes.
    """
    buckets = by_class(tree)
    assert set(buckets) == set(CLASSES)
    # structural, and said to be: by_class cannot drop a card, so this cannot
    # fail. The two assertions after it are what carry this test.
    assert sum(len(v) for v in buckets.values()) == len(scored_cards(tree))
    # an EQUALITY, and the reason is AC-4 itself: a scored card with no
    # '## Worktree notes' section is the shape ADR-0039/R2 makes a refusal, so
    # a member here is never a correct board operation.
    assert buckets[UNCLASSIFIABLE] == (), buckets[UNCLASSIFIABLE]

    historical = {
        name: len(buckets[name])
        for name in (NO_MARKER, MARKER_DISAGREES, SCORE_NAMES_NO_CYCLE)
    }
    assert sum(historical.values()) == 181, (
        f"the three declared historical classes now hold {sum(historical.values())} "
        "scored cards; the measured total is 181 (128 no-marker + 50 "
        "disagreeing + 3 naming no cycle). Every one of the three is "
        "closure-invariant, so a change here is a card that closed badly or a "
        f"population that moved, not a card that closed. {historical}"
    )
    assert len(buckets[AGREES]) >= 50, (
        f"{len(buckets[AGREES])} scored cards agree; the measured floor is 50"
    )
    # every scored card names a cycle or is one of the three declared
    named = len(scored_cards(tree)) - len(buckets[SCORE_NAMES_NO_CYCLE])
    assert named == len(scored_cards(tree)) - 3, (
        f"{len(buckets[SCORE_NAMES_NO_CYCLE])} scored cards name no review "
        "cycle; the declared population is 3 (measured at 228 of 231 naming "
        f"one). Members: {sorted(buckets[SCORE_NAMES_NO_CYCLE])}"
    )


def test_an_unclassifiable_card_is_a_failure_and_not_a_skip(tmp_path: Path) -> None:
    """AC-4's control: a scored card with no ``## Worktree notes`` section.

    Its marker count is neither zero nor a number. "No record" and "a record
    saying zero" are different facts **by this module's own reckoning** —
    unreadable against readable-and-empty, see :func:`worktree_notes` — and
    not because of anything the retrospective does with them; upstream maps
    both to one null and folds neither. ADR-0039/R2 makes the unreadable shape
    a refusal, so the walk reports it and the partition assertion above fails.
    It is never passed over.
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

    Dynamic — every file :func:`read_card_tree` actually **opened** is in
    ``git ls-files``. Static — no string literal in this module's executable
    code names ``meta/review``, **and no string used as a path segment is
    ``review``**, so nothing can reach the review YAMLs on a path this test's
    dynamic half does not walk.

    **The static half's reach was overstated and is now measured.** Its
    needles were ``meta/review`` and ``/review/`` — substrings containing a
    separator — while this module builds every path segment-by-segment
    (``REPO_ROOT / "meta" / "kanban" / "cards"``), so no string in its own path
    idiom contains a separator at all. Measured: adding ``REPO_ROOT / "meta" /
    "review"`` to executable code left **all 67 tests green**, and only the
    dynamic half catches a read of it, and only once something reads. So the
    static half now collects strings used **as path segments** — an operand of
    ``/``, an argument to ``Path(…)`` or ``.joinpath(…)`` — and refuses the
    segment ``review``. Scoped to segments rather than to every code string on
    purpose: this module's violation messages say "review cycle" in prose a
    dozen times, and a bare substring scan over all of them would be the
    self-seeing inspection one abstraction up. The substring needles are kept
    as the half that covers a written-out ``meta/review``.

    **The dynamic half observes the opens, it does not re-derive the
    returns.** It first checked the paths of the cards the tree reader
    *returned*, which is a weaker claim than the one made: a helper that
    opened some other file and returned nothing from it would not appear in
    that list at all, and only a review-directory-shaped *literal* would have
    been caught, by the static half. So the reader is now run inside an audit
    that wraps :meth:`pathlib.Path.read_text`, :func:`io.open` and
    :func:`builtins.open`, and the set of paths recorded is asserted to be
    **exactly** the set returned — an extra open reds, a missing one reds.

    **Which read routes the audit sees, measured rather than assumed.** With
    only ``Path.read_text`` and ``builtins.open`` wrapped, four of the six ways
    this interpreter (3.14.3) opens a file escaped it: ``Path.open``,
    ``Path.read_bytes``, ``io.open`` and ``os.open``. ``io.open is
    builtins.open`` is ``True``, but ``Path.open`` resolves ``io.open`` as a
    *module attribute*, which rebinding ``builtins.open`` never reaches — and
    the audit's own behaviour proved it, since one ``read_text`` recorded one
    entry rather than two. Wrapping ``io.open`` as well brings it to **five of
    six**: ``Path.open``, ``Path.read_bytes``, ``io.open``, ``builtins.open``
    and ``Path.read_text`` (which now records twice, harmlessly, because the
    recorded paths are compared as a set). **``os.open`` still escapes** — it
    is a raw file descriptor and no Python-level rebinding sees it — so the
    audit's reach is stated at five routes rather than at "every read".
    """
    tracked = _tracked_paths()
    assert tracked, "git ls-files returned nothing; the dynamic half is vacuous"
    read = [c.path.relative_to(REPO_ROOT).as_posix() for c in tree]
    assert read, "no card was read; the assertion below would be vacuous"
    assert [p for p in read if p not in tracked] == []
    assert all(p.startswith("meta/kanban/cards/") for p in read), read

    opened: list[str] = []
    real_read_text, real_open, real_io_open = Path.read_text, builtins.open, io.open

    def spy_read_text(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        opened.append(str(self))
        return real_read_text(self, *args, **kwargs)

    def spy_open(file, *args, **kwargs):  # type: ignore[no-untyped-def]
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    Path.read_text = spy_read_text  # type: ignore[method-assign]
    builtins.open = spy_open  # type: ignore[assignment]
    # the line that closes four of the six escape routes -- see the docstring
    io.open = spy_open  # type: ignore[assignment]
    try:
        audited_tree = read_card_tree()
    finally:
        Path.read_text = real_read_text  # type: ignore[method-assign]
        builtins.open = real_open  # type: ignore[assignment]
        io.open = real_io_open  # type: ignore[assignment]

    assert opened, "the open audit recorded nothing, so its assertions are vacuous"
    assert len(audited_tree) == len(tree), (
        f"the audited read returned {len(audited_tree)} cards and the fixture "
        f"{len(tree)}; the two are not reading the same tree"
    )

    def relative(raw: str) -> str:
        resolved = Path(raw).resolve()
        try:
            return resolved.relative_to(REPO_ROOT).as_posix()
        except ValueError:  # outside the repo: fails both assertions below
            return resolved.as_posix()

    audited = sorted({relative(p) for p in opened})
    assert audited == sorted(read), (
        "read_card_tree opened a set of paths that is not the set of cards it "
        f"returned. Opened and not returned: {sorted(set(audited) - set(read))}; "
        f"returned and not opened: {sorted(set(read) - set(audited))}"
    )
    assert [p for p in audited if p not in tracked] == [], (
        f"an untracked path was opened: {[p for p in audited if p not in tracked]}"
    )
    assert all(p.startswith("meta/kanban/cards/") for p in audited), audited

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

    # The substring half above is blind to the ONE path idiom this module
    # actually uses. `CARDS_DIR` is built segment-by-segment -- `REPO_ROOT /
    # "meta" / "kanban" / "cards"` -- so no string in it contains a separator
    # at all, and adding `REPO_ROOT / "meta" / "review"` to executable code
    # left all 67 tests green: only the dynamic half above would have caught a
    # read of it, and only once something actually read. A static claim that
    # cannot see its own module's spelling is a claim with no reach
    # (ADR-0039/R1), so the segments are collected as segments.
    #
    # Scoped to strings used AS path segments -- an operand of `/`, an argument
    # to `Path(...)` or `.joinpath(...)` -- and not to every code string,
    # because this module's own violation messages say "review cycle" in prose
    # a dozen times and a bare substring scan over all of them would red on
    # itself again, one abstraction up.
    segments: set[str] = set()

    def collect(node: ast.AST) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            segments.add(node.value)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            collect(node.left)
            collect(node.right)

    for node in ast.walk(module):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            collect(node.left)
            collect(node.right)
        elif isinstance(node, ast.Call):
            named = node.func.id if isinstance(node.func, ast.Name) else None
            attr = node.func.attr if isinstance(node.func, ast.Attribute) else None
            if named == "Path" or attr == "joinpath":
                for arg in node.args:
                    collect(arg)
    assert segments, "the segment walk found no path segments at all"
    # the control that this walk sees the idiom: CARDS_DIR's own segments
    assert {"meta", "kanban", "cards"} <= segments, sorted(segments)
    forbidden = "review"
    assert [s for s in segments if s.lower() == forbidden] == [], (
        f"a path segment {forbidden!r} is built in this module's executable "
        "code, so a guard here can reach the review directory on a path the "
        f"dynamic half only catches once something reads it: {sorted(segments)}"
    )


def test_the_estimate_unit_decision_still_has_no_adr_file() -> None:
    """The ref is upstream's, THIS series does not reach it — and that can fire.

    **The name of this test says "no ADR file" and that is scoped to this
    repository, which is the only thing it measures.** The decision does have
    an ADR: ``forge_1``'s 0055, accepted, see the module docstring, where the
    old flat claim is retracted. The name is left as it is because CARD-367's
    AC-4 names this function and owns updating it; renaming it from here would
    dangle that reference.

    **The pin's trigger is restated, because the old one was void.** It
    asserted ``max(numbers) == 42`` plus ``55 not in numbers`` and promised to
    "red the day someone writes it". The ADR was already written and dated
    2026-09-05, before the pin was; and this board will never number a
    *local* ADR 0055 for an upstream decision, so that arm was green and would
    have stayed green — a pin with no reachable failure is the gap
    ADR-0039/R1 names. Worse, the ``== 42`` arm would have red on a correct
    board operation: writing an unrelated ADR-0043.

    What can fire, and should: the **collision**. Six artefacts
    (``board.md``, ``dispatcher.state``, ``retro.md``, CARD-363, CARD-366,
    CARD-367) cite a bare ``ADR-0055`` meaning upstream's. The day this
    repository's own series reaches 0055, every one of those refs silently
    starts resolving to a local ADR about something else, and this test is
    where that is caught. The series head stays declared as a floor, so the
    measured residue (ADR-0039/R3) is still on the record without reddening a
    correct write.
    """
    adr_dir = REPO_ROOT / "meta" / "architecture" / "decisions" / "adr"
    numbers = sorted(int(p.name[:4]) for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert numbers, adr_dir
    assert max(numbers) >= 42, (
        f"this repository's ADR series now tops out at {max(numbers)}; the "
        "measured head when this was written is 0042, and a SHRINK means an "
        "ADR file was removed or renamed"
    )
    assert max(numbers) < 55, (
        f"this repository's ADR series has reached {max(numbers)}, so the bare "
        "`ADR-0055` refs on this board (board.md, dispatcher.state, retro.md, "
        "CARD-363, CARD-366, CARD-367) now resolve LOCALLY, to an ADR that is "
        "not the upstream estimate-unit decision they mean. Re-point them and "
        "re-point ESTIMATE_UNIT_FIRST_WAVE's comment; see CARD-367"
    )


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
    assertion is what keeps the guards from resting on it — **restated in
    cycle 3 to measure agreement instead of banning a spelling**: for every
    in-scope card, ``max`` over the score field and the highest ordinal the
    card's own markers carry name the same cycle. Two independently written
    records of one fact, compared. It is order-free and spelling-free, so a
    correct closure cannot red it, and it still fails the day the heuristic
    becomes load-bearing. See the comment at the assertion for the
    measurements, for the retraction of this module's CARD-020 framing, and
    for the one capability the trade cost.

    **The capability the trade cost, disclosed (ADR-0039/R3).** The
    replacement is weaker than the ban on exactly one shape, and it is the
    shape the ban was named for. Measured on a copy of main's cards, on
    in-scope CARD-348 (whose score is already ``cycle 1/3``, so the plant moves
    no spelling census): give it CARD-020's score spelling — ``7.5 (cycle 2;
    cycle 1 4.5; cycle 3 fixes applied, terminal)``, where ``max`` reads 3 for
    a card that scored on cycle 2 — and **forge its markers to agree with the
    misreading** (ordinals 1, 2, 3, so the highest marker ordinal is 3 too).
    The result is **68 passed, fully green**, while the ban's criterion reads
    ``['CARD-348.md']`` on the same plant and would have red. The **matched
    control** — the identical misread score with the card's real single marker
    — reds **4** tests, guard 1 among them. So the new check catches a misread
    only while the *other* record disagrees with it; forge both and it passes.

    Two lesser limits are documented in this module (a count sees that a
    population moved, never which cards moved; the open audit reaches five of
    six read routes) and this one was not, which is the gap being closed here
    rather than the trade being reversed. The ban's price was reddening on
    correct progression closures, and — measured on the unplanted tree — its
    live in-scope set was **empty**, so it bought this at the cost of a refusal
    nobody could reach (ADR-0039/R1).

    **The three counts are floors; the disjointness and the in-scope check are
    not.** Every count in this loop grows when a card is closed — a score
    written in the progression style (``7.75 (c1) → 8.5 (c2)``) adds to
    ``first_wrong``, one written ``8.5 (cycle 2/3)`` adds to
    ``n_of_m_blind`` — so equalities here red the suite on main for a correct
    closure, which is the defect this round came back on. A floor keeps the
    control's actual job, which is that neither naive reading may quietly stop
    discriminating, and the identity below keeps the loop honest: the blind and
    readable halves must still cover every card the loop considered.

    **The base of the blind figure is the cards that NAME a cycle, not the
    whole scored population.** The loop ``continue``\\ s past the three that
    name none before the check is reached, so 209 is 209 of **228** — and
    209 + 19 = 228 exactly. Over all 231, the figure is 212. Stating it
    against 231 was a declared bound naming a denominator that was not its
    own.
    """
    first_wrong, last_wrong, n_of_m_blind, n_of_m_readable = [], [], [], []
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
        else:
            n_of_m_readable.append(card.name)

    assert len(first_wrong) >= 11, (
        f"first-ordinal reading is wrong on only {len(first_wrong)} cards "
        f"(measured floor 11), so it has stopped discriminating: {first_wrong}"
    )
    assert len(last_wrong) >= 10, (
        f"last-ordinal reading is wrong on only {len(last_wrong)} cards "
        f"(measured floor 10), so it has stopped discriminating: {last_wrong}"
    )
    assert set(first_wrong).isdisjoint(last_wrong), (
        "the two naive readings now share a counterexample, so one of them "
        f"could be reached by narrowing the other: {set(first_wrong) & set(last_wrong)}"
    )
    # the spelling CARD-363's premise was measured with is blind to 209 of the
    # 228 that name a cycle at all -- NOT of the 231 scored (that figure is
    # 212). On main's tip the same three readings are 210, 229 and 213.
    considered = len(n_of_m_blind) + len(n_of_m_readable)
    assert considered == len(scored_cards(tree)) - 3, (
        f"the loop considered {considered} cards but {len(scored_cards(tree))} "
        "are scored and 3 name no cycle; the blind/readable split no longer "
        "covers the population it is a share of"
    )
    assert len(n_of_m_blind) >= 209, (
        f"`cycle N of M` alone cannot read {len(n_of_m_blind)} of the "
        f"{considered} scored cards that NAME a cycle; the measured floor is "
        "209 of 228 on the merge-base tree and 210 of 229 on main's tip. The "
        "floor carries the lower reading because INV-023 lets this module run "
        "against either tree; the arithmetic that holds on both is the "
        "identity asserted above, blind + readable == scored - 3"
    )
    assert len(n_of_m_readable) >= 19, (
        f"only {len(n_of_m_readable)} cards spell it `cycle N of M`; the "
        "measured floor is 19, identical on both trees"
    )
    # Guard 1 must not rest on the heuristic, and THIS is the honest proxy for
    # it: for every in-scope card, `max` over the free-text score field reads
    # the same cycle the card's own markers do. Order-free and spelling-free.
    #
    # What stood here before cycle 3 banned a SPELLING: no in-scope card may
    # be in `first_wrong | last_wrong`, with a message calling that
    # "deliberately stricter than `max` needs" and telling its reader to
    # re-spell the score. Removing it is not the loosening G-4 forbids -- it is
    # not a historical bound but a proxy for "the guard does not rest on the
    # heuristic", and that set is the wrong proxy, because it holds both kinds
    # of card at once. Measured: a progression score '7.75 (c1) -> 8.5 (c2/3)'
    # lands in first_wrong (ordinals 1,2) and `max` reads 2, which is RIGHT --
    # a correct closure the ban reds, and "re-spell the score" is wrong advice
    # for it; CARD-228's '8.0 (c1) -> 8.5 (c2) -> 8.0 (c3/3)' is a real card in
    # the same set with `max` reading 3 correctly; CARD-020's '7.5 (cycle 2;
    # cycle 1 4.5; cycle 3 fixes applied, terminal)' is in it too (ordinals
    # 2,1,3) and there `max` reads 3 for a card that scored on cycle 2 -- a
    # genuine misread. One set, opposite verdicts, so membership says nothing
    # about whether `max` is safe.
    #
    # RETRACTED IN PLACE, because this module was citing CARD-020 for more
    # than it can carry. The orchestrator's framing -- that the ban "missed" a
    # genuine misread -- is wrong twice and so is any reading of the paragraph
    # above that treats CARD-020 as a card the ban saw. The ban was
    # IN-SCOPE-ONLY (wave >= 74) and CARD-020 is **wave 13**; CARD-228 is wave
    # 42. Re-derived on main's cards: NO in-scope card is in
    # `first_wrong | last_wrong`, so the ban's live set was **empty** and it
    # was green and unreachable -- the ADR-0039/R1 gap, and a stronger ground
    # for removing it than any member of a set it could not see. What the two
    # out-of-scope cards do show is the SHAPE argument: order and correctness
    # are independent, in both directions, on real cards.
    #
    # Spelling is not the thing to test. Agreement between the two
    # independently written records of the same cycle is: this check is green
    # on the progression closure and red on the CARD-020 shape -- and green on
    # the CARD-020 shape if the markers are forged to agree with it, which is
    # the one capability the trade cost and is disclosed in the docstring.
    read_by_markers = {}
    for card in ran_in_a_wave(tree, ESTIMATE_UNIT_FIRST_WAVE):
        if card.status != "done" or not card.is_scored:
            continue
        section = worktree_notes(card.text) or ""
        ordinals = [
            int(found.group(1))
            for line in section.splitlines()
            if (found := _MARKER.match(line))
        ]
        if ordinals:
            read_by_markers[card.name] = (card.cycle_named, max(ordinals))
    assert read_by_markers, (
        "no in-scope card carries a marker, so the check below is vacuous and "
        "guard 1 could be resting on the heuristic unobserved"
    )
    disagreeing = {
        name: (named, highest)
        for name, (named, highest) in read_by_markers.items()
        if named != highest
    }
    assert disagreeing == {}, (
        "`max` over an in-scope card's Review score names a different cycle "
        "than the card's own highest marker ordinal, so guard 1 now RESTS on "
        "the heuristic: the two independent records of the same cycle "
        "disagree, and only one of them can be what the retrospective should "
        "read. Re-read the score field before touching this: the shape to "
        "fear is CARD-020's, where an earlier cycle is named after a later one "
        "and a THIRD number ('cycle 3 fixes applied') is not a cycle the card "
        f"ran at all. {disagreeing}"
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
        # a term that is PRESENT and still no denominator -- all three of these
        # passed guard 2 before cycle 3
        ("0c", None),
        ("0c (0.5d)", None),
        ("0.0c", None),
        # the one row in this corpus whose reading DEPENDS on stripping: the
        # `Nc` term is inside the comment, and the value outside it is days
        ("0.5d <!-- re-estimated from 2c at the re-cut -->", None),
    ],
)
def test_estimate_cycles_reads_the_nc_term(value: str, expected: float | None) -> None:
    """Including the zero term, and the one row stripping actually changes."""
    assert estimate_cycles(value) == expected, value


def test_comment_stripping_discriminates_on_the_shape_the_tree_lacks() -> None:
    """The module's only control that separates the two comment readings.

    Comment stripping is **measured inert** on this board — 0 of 372 ``Wave``,
    ``Estimate`` and ``Review score`` readings change with the comments left in
    (see the module docstring). So no row of any corpus here, and no plant on
    any real card, can show that the stripping does anything: the two
    parametrized rows once advertised as "the two shapes the comment trap
    produces" return the same value either way, and so does the planted
    comment-behind-an-estimate card in
    :func:`test_a_cycle_estimate_hidden_behind_an_inline_comment_still_counts`.
    A mechanism with no control that can fail is the gap ADR-0039/R1 names, and
    this is the control: a day-only estimate whose **comment** mentions an
    ``Nc`` term, where the unstripped read takes the retired number out of the
    comment and the stripped read correctly sees no cycle estimate at all.

    This is the shape the stripping exists for, and it is a plausible next
    board write — ``Estimate: 0.5d <!-- re-estimated from 2c -->`` is how this
    board already annotates a re-estimate on other fields.
    """
    value = "0.5d <!-- re-estimated from 2c at the re-cut -->"
    unstripped = _ESTIMATE_CYCLES.search(value)
    assert unstripped is not None and float(unstripped.group(1)) == 2.0, value
    assert _ESTIMATE_CYCLES.search(strip_comments(value)) is None, value
    assert estimate_cycles(value) is None, value
    # and the contrast: the trap row that does NOT discriminate, kept to show
    # which of the two kinds each corpus row is
    inert = "0.75d  <!-- was 0.25d; raised by the CARD-264 fold -->"
    assert _ESTIMATE_CYCLES.search(inert) is None, inert
    assert estimate_cycles(inert) is None, inert


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

    **7** cards carry a comment on ``Estimate`` and **15** on ``Wave`` on the
    merge-base tree, **16** on main's tip. That is this module's own
    measurement and it is attributed to nobody else.

    **Both are FLOORS, and the equalities they replace red on main right now.**
    Each census counts a comment the board writes as a *correct* operation: a
    wave open stamps ``Wave: 77 <!-- dispatched … -->``, a re-stamp annotates
    the value it replaces, and a re-cut annotates ``Estimate`` — CARD-322's
    was written on 2026-10-31. Measured: ``len(wave) == 15`` reads **16** on
    main's tip and reds, because wave 76's close re-stamped *this module's own
    card* from ``76`` to ``77 <!-- RE-STAMPED … -->``. This round had already
    declined to assert an inertness *count* for comment stripping on exactly
    this ground (see
    :func:`test_comment_stripping_discriminates_on_the_shape_the_tree_lacks`)
    and did not carry the reasoning one field over to the comment counts
    themselves. The floors carry both readings so the bound is still declared
    and a *shrink* — a comment removed, or a field that stopped parsing — still
    reds.

    The floor figure is the **merge-base** one, not main's, because INV-023
    means this module can be run from a tree that predates main's writes; a
    floor of 16 would red on this branch for no board reason. See the module
    docstring.

    **A quotation is retracted here.** This docstring used to read: *CARD-363
    states "two cards carry an inline comment on a parsed field today"*.
    CARD-363 never said it — not in any version of the card; a pickaxe search
    over all history finds that sentence in exactly one commit, this module's
    own first one. What the board really says, and what the figure 2 came
    from, is a ``meta/kanban/dispatcher.state`` note from CARD-278's board
    pass: an inline comment on ``Revision pending`` made an equality test read
    CARD-288 as un-gated and corrupted a census while it was being re-derived,
    and "two cards carry an inline comment on a parsed field here: CARD-288 and
    CARD-322". That note is about a **different field** and a **different
    census**, and it is right about its own: CARD-288 still carries the comment
    on ``Revision pending`` (the only card that does today) and CARD-322's has
    since moved to ``Estimate``. So the 2 was never a claim about ``Estimate``
    and ``Wave``, and the 7 and the 15 do not correct it — they measure
    something else. In a module whose subject is records that do not say what
    they claim, a quotation put in a card's mouth is the defect itself.
    """
    est = sorted(c.name for c in tree if "<!--" in c.raw_estimate)
    wave = sorted(c.name for c in tree if "<!--" in c.raw_wave)
    assert len(est) >= 7, (
        f"{len(est)} cards carry a comment on Estimate; the declared floor is "
        "7 (7 on the merge-base tree, 7 on main's tip). A floor, because a "
        "re-cut annotates Estimate inline as a correct board operation. A "
        f"SHRINK means a comment was removed or the field stopped parsing: {est}"
    )
    assert len(wave) >= 15, (
        f"{len(wave)} cards carry a comment on Wave; the declared floor is 15 "
        "(15 on the merge-base tree, 16 on main's tip — CARD-363's own "
        "re-stamp). A floor, because a wave open and a re-stamp both annotate "
        "Wave inline as correct board operations. A SHRINK means a comment was "
        f"removed or the field stopped parsing: {wave}"
    )

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

    **The claim this docstring used to make is RETRACTED as false.** It said:
    "Without stripping, 15 cards would read as unscheduled and drop out of
    guard 2's population entirely". They would not. ``_LEADING_WAVE`` is
    anchored ``^(\\d+)\\b`` and reads ``68 <!-- … -->`` as 68 with the comment
    still in it, so **none** of the 15 drops out, and stripping changes 0 of
    372 ``Wave`` readings, 0 of 372 ``Estimate`` readings and 0 of 372 cycle
    readings on main's tree. Cycle 1 of this card's review endorsed the false
    version by substituting a *bare-integer* reading for the module's anchored
    one — a different parser than the one that ships here.

    Stripping is kept because it is right for a shape the tree does not carry
    yet, and that shape now has the module's only discriminating control:
    :func:`test_comment_stripping_discriminates_on_the_shape_the_tree_lacks`.
    What is asserted *here* is what is true of the real values — every
    contaminated one is still interpretable, and no comment sits where it would
    change an already-readable number.

    **A second assertion of this test is retracted and replaced, and it is the
    sharpest cell of the three that red on main.** It forbade any card at or
    after the forward boundary from carrying a comment on its ``Wave`` field at
    all — which forbids the **dispatch convention by construction**, since a
    wave open writes ``Wave: 77 <!-- dispatched … -->``. It counted nothing,
    its own comment conceded it had no members ("none today"), and the reason
    it gave for existing (keeping the twin non-vacuous) was already covered by
    ``assert contaminated`` above. On main's tip it reads ``['CARD-363.md']``.
    See the comment at its replacement for the full retraction and for why the
    one-sided shape ``shifted`` already used is the one to copy.
    """
    contaminated = [c for c in tree if "<!--" in c.raw_wave]
    assert contaminated, "vacuous: no contaminated Wave field on the tree"

    def unstripped_wave(raw: str) -> int | None:
        found = _LEADING_WAVE.match(raw.strip())
        return int(found.group(1)) if found else None

    # What stood here was `all(... is None for ...) is False`, which asserts
    # only that at least ONE contaminated raw value still starts with a digit
    # -- true, and the opposite of what the docstring claimed stripping buys.
    # The assertion that has teeth and cannot red on a correct board operation
    # is one-sided: where the naive reading does produce a number, stripping
    # must not CHANGE it. A comment can only alter an anchored reading by
    # sitting at the start of the value (naive reads None, not a different
    # number) or INSIDE the leading digit run -- `Wave: 7<!--x-->6`, which
    # would read 7 naively and 76 stripped. That is a real trap and not a
    # thing a correct stamp does.
    shifted = [
        (c.name, unstripped_wave(c.raw_wave), c.wave)
        for c in contaminated
        if (naive := unstripped_wave(c.raw_wave)) is not None and naive != c.wave
    ]
    assert shifted == [], (
        "an inline comment sits inside a Wave value's leading digits, so the "
        "stripped and unstripped readings are two different numbers rather "
        f"than one number and None: {shifted}"
    )
    naive = [c.name for c in contaminated if not re.fullmatch(r"\d+", c.raw_wave)]
    assert len(naive) == len(contaminated), naive
    assert all(c.wave is not None for c in contaminated)

    # RETRACTED AND REPLACED, not deleted. What stood here was
    # `in_scope_but_contaminated == []`, under the comment "none today; the
    # assertion exists so the twin above cannot go vacuous". Both halves of
    # that were wrong.
    #
    # It did not keep anything from going vacuous: `assert contaminated` at the
    # top of this test is the anti-vacuity control, and `shifted` below it
    # already covers every contaminated card, in-scope ones included. What the
    # assertion DID do was forbid the dispatch convention by construction --
    # it refused ANY card at or after the forward boundary carrying a comment
    # on its `Wave` field at all, and a wave open writes exactly that:
    # `Wave: 77 <!-- dispatched ... -->` on a ready card. Measured on main's
    # tip: it reads ['CARD-363.md'] and reds, because wave 76's close
    # re-stamped THIS module's own card from 76 to `77 <!-- RE-STAMPED ... -->`.
    # So the version of this module that passed 67/67 on the branch would have
    # turned main red on a correct board write, and the remedy it implied was
    # to strip a correct re-stamp note off a card: the board bending to the
    # test.
    #
    # The replacement is one-sided and spelling-free, like `shifted`: the wave
    # the FIELD states must be the number written BEFORE the comment. That is
    # the property a dispatch note has and `Wave: 7<!--x-->6` does not, it is
    # green on every shape the convention produces, and it has teeth the twin
    # lacks -- `shifted` compares two readings of the raw value and cannot see
    # a value whose pre-comment text is not the number at all (`<!--x-->77`
    # reads None naive, 77 stripped, and passes `shifted`).
    mislabelled = [
        (c.name, c.raw_wave.split("<!--", 1)[0].strip(), c.wave) for c in contaminated
    ]
    assert [row for row in mislabelled if row[1] != str(row[2])] == [], (
        "a card's Wave comment does not sit AFTER the wave the field states, "
        "so the number this module reads is not the number a human reading "
        "the line sees: "
        f"{[row for row in mislabelled if row[1] != str(row[2])]}"
    )
    # Reported, never banned. In-scope members are the dispatch convention
    # working: 0 on the merge-base tree, 1 on main's tip (CARD-363). They are
    # what makes the check above non-vacuous for in-scope cards for the first
    # time.
    #
    # And the one thing that must hold about them is the harm the retracted
    # claim at the top of this docstring misdescribed: a comment must never
    # cost a card its place in a guard's population. Stated as a SUBSET, so an
    # in-scope card the naive reading misses (`<!--x-->77`) is fine and an
    # in-scope card the stripped reading misses is not. Not structural:
    # `ran_in_a_wave` reads the stripped value, the set below reads the raw
    # one, and a strip that mangled a leading digit run would break it.
    stripped_in_scope = {c.name for c in ran_in_a_wave(tree, ESTIMATE_UNIT_FIRST_WAVE)}
    naive_in_scope = {
        c.name
        for c in tree
        if (n := unstripped_wave(c.raw_wave)) is not None
        and n >= ESTIMATE_UNIT_FIRST_WAVE
    }
    assert naive_in_scope <= stripped_in_scope, (
        "a card the raw Wave value puts in the guards' scope is NOT in the "
        "scope the stripped value computes, so comment stripping has cost a "
        f"card its place in a guard's population: {naive_in_scope - stripped_in_scope}"
    )


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
