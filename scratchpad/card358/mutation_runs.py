"""CARD-358 AC-4 — every repaired claim is re-broken by a planted mutant.

Each of the four claims CARD-358 re-expressed gets **two** mutants: the obvious
one (the thing the claim names stops being true) and an **edge** one (the claim
loses its subject, or its cross-check stops being independent, without anything
visibly breaking). The edge mutants are the point: a re-expression that reads
the converted medium can be satisfied by an empty reading, and that is the
failure mode the seven reds were themselves an instance of.

Discipline, per the board's mutation rules:

* ``PYTHONDONTWRITEBYTECODE=1`` and ``__pycache__`` swept at both ends;
* every plant is **by text**, with its occurrence count asserted ``== 1``
  before the substitution, so a moved or re-worded site is a refusal rather
  than a silent no-op;
* every file is SHA-256'd before and after, and **restored from the content
  captured in this process** -- never ``git checkout``, which would also
  revive anything else the tree happened to be carrying;
* every run is under CARD-338's five-kind probe, because the reds these
  repairs answer are a property of the converted end state and not of the
  tree -- unplanted and unlifted, the module is 52 passed;
* ``0 skipped`` is asserted on every run, and the run is the impact scope
  (CARD-358's one module). The ``db_required`` gate and the ``setrlimit`` skip
  are both outside this selection.

Every mutant names its **matched control**: node ids that must stay GREEN in
the same run. A mutant that reds the whole module has broken collection or the
fixtures, not the claim, and tells you nothing.

``src/`` is read, never edited (CARD-358 G-1): every plant below is restored
byte-identically in the same process and the SHA-256 pair is the proof. G-3
allows exactly this -- a plant in a sibling's file is a measurement; an edit
left there is the violation.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PYTHON = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"
MODULE = "tests/test_book_interior_type_floor.py"
PROBE = "scratchpad.card338.probe_five_kinds"


@dataclass(frozen=True)
class Mutant:
    name: str
    claim: str
    edge: bool
    #: ``{path relative to ROOT: [(exact text to find, replacement)]}``
    plants: Dict[str, List[Tuple[str, str]]]
    #: Node id substrings that MUST red.
    must_red: Tuple[str, ...]
    #: Node id substrings that MUST stay green in the same run -- the control.
    must_stay_green: Tuple[str, ...]
    why: str = ""
    #: A phrase the run's output must carry, so a kill is the assertion this
    #: mutant aims at rather than a collateral error on the way to it.
    expect_in_output: str = ""


DRAW = "src/nonogram/admin/book_vector_draw.py"
GUIDE = "src/nonogram/admin/book_guide_vector.py"
ANSWER = "src/nonogram/admin/book_answer_vector.py"
TOC = "src/nonogram/admin/book_toc_vector.py"
PUZZLE = "src/nonogram/admin/book_puzzle_vector.py"
GENERATOR = "src/nonogram/admin/book_pdf_generator.py"


MUTANTS = (
    # ---------------------------------------------------------------- claim 1
    Mutant(
        name="divider-letters-nothing",
        claim="the semantic coverage requirement (reds 1-2)",
        edge=False,
        plants={
            GENERATOR: [
                (
                    '        draw.text((x, y), text, fill="black", font=divider_font)',
                    "        pass  # MUTANT: the divider's own word is not set",
                ),
                (
                    "            content_bottom=y + bbox[3],\n        )\n        return divider",
                    "            content_bottom=y + bbox[3],\n"
                    "        ) if False else None  # MUTANT: nor its folio\n"
                    "        return divider",
                ),
            ]
        },
        must_red=("test_the_recording_covers_every_kind_of_interior_lettering",),
        must_stay_green=(
            "test_the_exemption_rule_by_name",
            "test_the_semantic_kinds_are_mapped_to_page_kinds",
        ),
        why=(
            "divider is the one semantic kind still set on a raster page once "
            "the five convertible kinds lift, so it IS the whole of the "
            "derived requirement. Both of the page's text calls are dropped: "
            "the first attempt dropped only the divider word and the test "
            "stayed green, because _draw_folio runs from inside "
            "create_divider_page and so its folio is tagged 'divider' too -- "
            "a reminder that TextCall.kind keys on the whole chain"
        ),
    ),
    Mutant(
        name="divider-declared-vector",
        claim="the semantic requirement's non-vacuity guard (reds 1-2, edge)",
        edge=True,
        plants={
            GENERATOR: [
                (
                    "    return PageMedium.RASTER if kind in _RASTER_DECLARATIONS else PageMedium.VECTOR",
                    "    if kind is PageKind.DIVIDER:  # MUTANT: the last raster interior kind converts\n"
                    "        return PageMedium.VECTOR\n"
                    "    return PageMedium.RASTER if kind in _RASTER_DECLARATIONS else PageMedium.VECTOR",
                )
            ]
        },
        must_red=("test_the_recording_covers_every_kind_of_interior_lettering",),
        must_stay_green=(
            "test_the_exemption_rule_by_name",
            "test_the_semantic_kinds_are_mapped_to_page_kinds",
        ),
        expect_in_output="has gone vacuous",
        why=(
            "THE edge mutant for this repair. With divider vector too, "
            "semantic_kinds_lettered_in_raster() returns the empty set and the "
            "requirement becomes `set() <= kinds` -- true of any reading "
            "whatsoever. Without the `assert required` default-deny guard the "
            "repair would read GREEN over a claim that had ceased to exist, "
            "which is the shape of the seven reds it answers. Planted in "
            "page_medium rather than in _RASTER_DECLARATIONS on purpose: the "
            "probe asserts the dict still declares exactly COVER and DIVIDER, "
            "so removing the entry is refused by the instrument before any "
            "test runs and measures nothing"
        ),
    ),
    # ---------------------------------------------------------------- claim 2
    Mutant(
        name="no-clue-digit-mark",
        claim="the exemption's non-vacuity floor (reds 3-4)",
        edge=False,
        plants={
            DRAW: [
                (
                    "    stream.begin_marked(CLUE_DIGIT_TAG)",
                    "    pass  # MUTANT: no mark emitted",
                ),
                (
                    "        stream.end_marked()",
                    "        pass  # MUTANT: and the pair dropped together",
                ),
            ]
        },
        must_red=("test_the_exempt_set_is_non_empty",),
        must_stay_green=("test_the_exemption_rule_by_name",),
        expect_in_output="owes this page its mark",
        why=(
            "the writer stops claiming provenance, so the stream arm exempts "
            "nothing; the spy arm is already empty in the converted medium, so "
            "the union is empty and the floor would hold vacuously over the "
            "very faces the exemption exists for. Dropped as a PAIR so the "
            "stream stays balanced and what is measured is the missing mark "
            "rather than an unreadable extent.\n\n"
            "MEASURED, and it corrected a prediction: the kill arrives through "
            "faces_on_page's own missing-mark refusal rather than through "
            "`assert exempt`, because stream_recording() refuses the page "
            "before the union is ever formed. That refusal is CARD-314 AC-3 "
            "and is the right answer -- but it means this mutant does NOT "
            "exhibit the new guard's own message. "
            "`neither-kind-draws-clue-digits` below is the one that does"
        ),
    ),
    Mutant(
        name="answer-stops-drawing-clue-digits",
        claim="the exemption's non-vacuity floor (reds 3-4, edge)",
        edge=True,
        plants={
            ANSWER: [
                (
                    "    draw_clue_digits(stream, slot, face, grey=grey)",
                    "    pass  # MUTANT: the answer page sets no clue digit",
                )
            ]
        },
        must_red=("test_the_refused_kinds_are_derived_and_agree_with_the_spy",),
        must_stay_green=(
            "test_the_exempt_set_is_non_empty",
            "test_every_face_outside_the_exemption_is_at_least_ten_points",
        ),
        why=(
            "the edge mutant for the exemption, and it is deliberately NOT the "
            "non-vacuity floor that catches it: the answer page's 258 exempt "
            "digits go, the puzzle page's 204 stay, so `assert exempt` is "
            "still satisfied -- a count is the wrong instrument for a kind "
            "going missing, and the cross-check agrees too because BOTH its "
            "readings narrow together, which is correct. What has to catch it "
            "is something else -- and MEASURING it corrected the "
            "prediction written here first, which said the floor. It is not "
            "the floor: the answer page's digits are not shrunk, they are not "
            "drawn, so there is no sub-floor face left to report and the floor "
            "is green. What catches it is the cross-check's LITERAL -- "
            "`by_the_readers == {'answer', 'puzzle'}`, cycle 1's F-001 "
            "direction -- which pins that two kinds draw clue digits and not "
            "one. The exemption's own count stays green and is right to: the "
            "puzzle page's 204 exempt digits are still there. So the three "
            "repaired claims do divide the work, just not the way predicted"
        ),
    ),
    Mutant(
        name="neither-kind-draws-clue-digits",
        claim="the exemption's non-vacuity floor (reds 3-4, edge)",
        edge=True,
        plants={
            ANSWER: [
                (
                    "    draw_clue_digits(stream, slot, face, grey=grey)",
                    "    pass  # MUTANT: no answer-page clue digit",
                )
            ],
            PUZZLE: [
                (
                    "    draw_clue_digits(stream, layout, measured, grey=grey)",
                    "    pass  # MUTANT: no puzzle-page clue digit either",
                )
            ],
        },
        must_red=("test_the_exempt_set_is_non_empty",),
        must_stay_green=(
            "test_the_exemption_rule_by_name",
            "test_the_semantic_kinds_are_mapped_to_page_kinds",
        ),
        expect_in_output="neither arm of the reading found a single exempt face",
        why=(
            "the mutant that reaches the new guard's own assertion, and the "
            "only one that can. CON-020's exemption exists on exactly two page "
            "kinds and both convert, so while either still draws its digits "
            "something else speaks first: faces_on_page's missing-mark refusal "
            "if the mark goes, the cross-check's literal if one kind goes. The "
            "exemption is empty only when BOTH kinds stop drawing -- and then "
            "CLUE_DIGIT_KINDS is empty too, so no refusal fires, no literal is "
            "contradicted, every face in both books holds the 10 pt floor "
            "honestly, and the module would read GREEN over a constraint that "
            "had lost its entire exempt population. That is the vacuum "
            "`assert exempt` is for, and it is the one this card's own red "
            "(`assert []`) was an instance of"
        ),
    ),
    # ---------------------------------------------------------------- claim 3
    Mutant(
        name="guide-exempts-its-clue-digits",
        claim="the worked example is never exempt (reds 5-6)",
        edge=False,
        plants={
            GUIDE: [
                (
                    "EXEMPT_KINDS: frozenset = frozenset()",
                    "EXEMPT_KINDS: frozenset = frozenset({CLUE_DIGIT})  # MUTANT",
                )
            ]
        },
        must_red=("test_worked_example_digits_are_drawn_and_never_exempt",),
        must_stay_green=("test_the_exempt_set_is_non_empty",),
        expect_in_output="NEVER exempt",
        why=(
            "the guide writer claims CON-020's exemption for the reader's own "
            "instruction text -- CARD-296 AC-5 inverted. In the converted "
            "medium the stream carries no mark to contradict it, so the "
            "writer's declaration IS the claim and has to be read"
        ),
    ),
    Mutant(
        name="guide-digits-tagged-as-body-text",
        claim="the worked example is drawn (reds 5-6, edge)",
        edge=True,
        plants={
            GUIDE: [
                (
                    "        drawn.append(DrawnFace(CLUE_DIGIT, text, size_pt))",
                    "        drawn.append(DrawnFace(BODY_TEXT, text, size_pt))  # MUTANT",
                )
            ]
        },
        must_red=("test_worked_example_digits_are_drawn_and_never_exempt",),
        must_stay_green=("test_the_exempt_set_is_non_empty",),
        expect_in_output="the worked example drew no clue digit",
        why=(
            "THE edge mutant for this repair. Nothing visibly breaks: the "
            "digits are still drawn, still reach the stream, still hold the "
            "floor. Only the provenance the re-expression depends on is gone, "
            "so guide_clue_digit_faces() returns [] and the claim has no "
            "subject -- the same silent emptying that made the raster reading "
            "go quiet in the first place. `assert digits` must red"
        ),
    ),
    # ---------------------------------------------------------------- claim 4
    Mutant(
        name="drawer-reached-through-an-alias",
        claim="the derived set's independent second reading (red 7, edge)",
        edge=True,
        plants={
            ANSWER: [
                (
                    "    draw_clue_digits(stream, slot, face, grey=grey)",
                    "    _alias = draw_clue_digits  # MUTANT: the AST walk cannot see the name\n"
                    "    _alias(stream, slot, face, grey=grey)",
                )
            ]
        },
        must_red=("test_the_refused_kinds_are_derived_and_agree_with_the_spy",),
        must_stay_green=(
            "test_the_exemption_rule_by_name",
            "test_the_semantic_kinds_are_mapped_to_page_kinds",
        ),
        why=(
            "cycle 1's F-001 direction, in the converted medium. The page is "
            "unchanged -- same digits, same mark, same sizes -- but "
            "called_names() no longer sees `draw_clue_digits`, so "
            "CLUE_DIGIT_KINDS silently narrows to {'puzzle'} and the answer "
            "page's 258 exempt digits would start being reported as CON-020 "
            "violations. The derivation cannot catch this; only a reading that "
            "shares no code with it can, and the spy was that reading until "
            "the answer page converted. The stream arm is now that reading"
        ),
    ),
    Mutant(
        name="derivation-over-reads-the-toc",
        claim="the derived set's independent second reading (red 7)",
        edge=False,
        plants={
            TOC: [
                (
                    "@dataclass(frozen=True)\nclass TocTypeSpec:",
                    "def _mutant_never_called(stream, layout, face):  # MUTANT\n"
                    "    from nonogram.admin.book_vector_draw import draw_clue_digits\n"
                    "    draw_clue_digits(stream, layout, face)\n"
                    "\n"
                    "\n"
                    "@dataclass(frozen=True)\nclass TocTypeSpec:",
                )
            ]
        },
        must_red=("test_the_refused_kinds_are_derived_and_agree_with_the_spy",),
        must_stay_green=(
            "test_the_exemption_rule_by_name",
            "test_the_semantic_kinds_are_mapped_to_page_kinds",
        ),
        why=(
            "the other direction: the derivation OVER-reads. A call to the "
            "drawer in code no TOC page ever reaches is still a Call node, so "
            "CLUE_DIGIT_KINDS widens to {'answer', 'puzzle', 'toc'} while the "
            "shipped file marks nothing on a TOC page -- and the two readings "
            "part company. The replaced mutant for this claim was a rename of "
            "`draw_clue_digits` itself, which turns out to be UNREACHABLE as a "
            "test-level kill: both page modules bind the name with "
            "`from ... import`, so a rename is an ImportError at collection "
            "and the module's own hasattr guard never gets to speak. That is "
            "reported as a finding rather than repaired"
        ),
    ),
)

def sweep() -> None:
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> subprocess.CompletedProcess:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=".")
    return subprocess.run(
        [
            PYTHON, "-m", "pytest", "-p", PROBE, MODULE,
            "-o", "addopts=", "-q", "-rEfs", "--no-header",
        ],
        cwd=ROOT, env=environment, capture_output=True, text=True,
    )


def tally(output: str) -> Dict[str, int]:
    for line in reversed(output.splitlines()):
        if " passed" in line or " failed" in line or " error" in line:
            counts = {}
            for part in line.replace("=", " ").split(","):
                words = part.split()
                for index, word in enumerate(words):
                    if word.isdigit() and index + 1 < len(words):
                        counts[words[index + 1].strip()] = int(word)
            if counts:
                return counts
    return {}


def failed_nodes(output: str) -> List[str]:
    return [
        line.split(" ", 1)[1].strip()
        for line in output.splitlines()
        if line.startswith("FAILED ") or line.startswith("ERROR ")
    ]


#: CARD-322's M1 red, which this card does NOT own and leaves standing: the
#: ``monkeypatch.delitem`` site on ``PageKind.TITLE``. It is expected in every
#: run below and is never counted as a mutant's kill.
M1 = "test_lifting_a_declaration_makes_the_stream_arm_read_that_page"


def main() -> int:
    sweep()
    paths = {name: ROOT / name for name in {DRAW, GUIDE, ANSWER, TOC, PUZZLE, GENERATOR}}
    before = {name: digest(path) for name, path in paths.items()}
    originals = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}

    baseline = run()
    base_counts = tally(baseline.stdout)
    base_failed = failed_nodes(baseline.stdout)
    print(f"BASELINE (probe, unplanted): {base_counts}")
    print(f"  failed: {[node.split('::')[-1] for node in base_failed]}")
    assert base_counts.get("skipped", 0) == 0, f"0 skipped required: {base_counts}"
    assert [node for node in base_failed if M1 not in node] == [], (
        "the impact-scoped baseline carries a red this card does not own and "
        f"did not expect: {base_failed}"
    )
    assert any(M1 in node for node in base_failed), (
        "CARD-322's M1 red is gone from the baseline. This card must leave it "
        "standing -- a card that repairs its neighbour's red hides which card "
        "the repair belonged to"
    )

    verdicts = []
    for mutant in MUTANTS:
        for name, replacements in mutant.plants.items():
            text = originals[name]
            for old, new in replacements:
                occurrences = text.count(old)
                assert occurrences == 1, (
                    f"{mutant.name}: the plant site occurs {occurrences} times "
                    f"in {name}, not once -- refusing to plant a mutant that "
                    f"may be a no-op or may hit more than one site:\n{old!r}"
                )
                text = text.replace(old, new)
            paths[name].write_text(text, encoding="utf-8")
        sweep()
        try:
            result = run()
        finally:
            for name in mutant.plants:
                paths[name].write_text(originals[name], encoding="utf-8")
            sweep()
            for name in mutant.plants:
                assert digest(paths[name]) == before[name], (
                    f"{mutant.name}: {name} did not restore byte-identically"
                )

        counts = tally(result.stdout)
        failed = failed_nodes(result.stdout)
        killed = [
            target for target in mutant.must_red
            if any(target in node for node in failed)
        ]
        control_red = [
            target for target in mutant.must_stay_green
            if any(target in node for node in failed)
        ]
        edge = "EDGE " if mutant.edge else "     "
        message_seen = (
            mutant.expect_in_output in result.stdout
            if mutant.expect_in_output else None
        )
        ok = (
            len(killed) == len(mutant.must_red)
            and not control_red
            and message_seen is not False
        )
        print(f"\n{edge}{mutant.name}  [{mutant.claim}]")
        print(f"        {counts}")
        print(f"        re-broke: {killed or 'NOTHING -- the repair does not bite'}")
        if mutant.expect_in_output:
            print(f"        its own message in the output: {message_seen}"
                  f"  ({mutant.expect_in_output!r})")
        print(f"        control green: {not control_red}"
              + (f"  (RED: {control_red})" if control_red else ""))
        assert counts.get("skipped", 0) == 0, f"0 skipped required: {counts}"
        verdicts.append((mutant.name, ok))

    for name, path in paths.items():
        assert digest(path) == before[name], f"{name} left edited"
    print("\nall src/ files restored byte-identically (SHA-256 pairs match)")

    bad = [name for name, ok in verdicts if not ok]
    print(f"\n{len(verdicts) - len(bad)}/{len(verdicts)} mutants re-broke their claim")
    if bad:
        print(f"NOT re-broken: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
