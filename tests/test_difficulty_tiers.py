"""COMP-006/COMP-001 tests: FR-008's tier selector and ADR-0005's cutoffs.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-020  TestSelectDifficulty_AcceptsValidTier  -> test_accepts_valid_tier*
    AC-021  TestSelectDifficulty_RejectsUnknownTier -> test_rejects_unknown_tier*

Two halves, matching the two things "a tier" has to be.

*The bands* (``nonogram.difficulty``): ADR-0005 splits the 0..100 scale into
three equal tertiles, and the tests below pin the cutoffs, the ends they belong
to, and — the one that matters most for a tunable table — that the bands and
the classifier are derived from the same two constants, so moving a cutoff
moves both together. A test that restated ``33``/``66`` as its own expectation
would only be pinning the current tuning; these pin the *structure* and check
the numbers once, against ADR-0005 directly.

*The selector* (``nonogram.cli`` -> ``nonogram.orchestrator``): the tier a user
types survives the trip inward as a tier the aggregate carries (AC-020), and a
tier that does not exist is refused by the domain rather than by argparse
(AC-021, guardrail G-4) — with the tool's own message and exit code, not
argparse's usage error.

The resample loop those bands drive is ``tests/test_resample.py``; this module
stops at "which band is this score in, and which band did the user ask for".
"""

from __future__ import annotations

import ast
import inspect
import itertools
import warnings
from pathlib import Path

import pytest

from nonogram import cli, difficulty, orchestrator
from nonogram.difficulty import (
    EASY_MAX_SCORE,
    MEDIUM_MAX_SCORE,
    SCORE_MAX,
    SCORE_MIN,
    TIER_BANDS,
    Tier,
    classify,
    parse_tier,
    tier_of_record,
)
from nonogram.errors import GenerationAbandoned, UnsupportedDifficulty
from nonogram.orchestrator import GenerationRequest, Puzzle

# --------------------------------------------------------------------------
# ADR-0005's cutoffs
# --------------------------------------------------------------------------


def test_the_scale_is_split_into_the_three_tertiles_adr_0005_names() -> None:
    """ADR-0005: Easy [0, 33], Medium (33, 66], Hard (66, 100].

    The one place the ADR's literal numbers are asserted. Everything else in
    this module reads them from the module, so a retune moves one test rather
    than a dozen — which is what makes the table tunable in practice and not
    just in principle.

    **Unchanged by ADR-0029, and that is the point of guardrail G-5.** The
    strategy ladder was mapped onto these two constants rather than the other
    way round (``simple_overlap`` 0..33, ``line_dp`` 33..66,
    ``probe_contradiction`` 66..100), so no stored grade moved on account of a
    band edge. The recalibration ADR-0005 is still owed — whether the
    within-rung share spreads puzzles usefully inside a band — is recorded with
    CARD-076's AC-118 distribution and deliberately not done there.
    """
    assert EASY_MAX_SCORE == 33.0
    assert MEDIUM_MAX_SCORE == 66.0
    assert TIER_BANDS[Tier.EASY] == (SCORE_MIN, EASY_MAX_SCORE)
    assert TIER_BANDS[Tier.MEDIUM] == (EASY_MAX_SCORE, MEDIUM_MAX_SCORE)
    assert TIER_BANDS[Tier.HARD] == (MEDIUM_MAX_SCORE, SCORE_MAX)


def test_the_three_bands_tile_the_whole_scale_without_gap_or_overlap() -> None:
    """Every band ends where the next begins, and together they are 0..100.

    Structural, so it survives a retune: a cutoff pair that left a gap would
    give some scores no tier, and one that overlapped would give some two.
    """
    bands = [TIER_BANDS[tier] for tier in (Tier.EASY, Tier.MEDIUM, Tier.HARD)]
    assert bands[0][0] == SCORE_MIN
    assert bands[-1][1] == SCORE_MAX
    for (_, previous_high), (next_low, _) in itertools.pairwise(bands):
        assert previous_high == next_low
    for low, high in bands:
        assert low < high


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        pytest.param(SCORE_MIN, Tier.EASY, id="floor-of-the-scale"),
        pytest.param(1.0, Tier.EASY, id="inside-easy"),
        pytest.param(EASY_MAX_SCORE, Tier.EASY, id="easy-cutoff-belongs-to-easy"),
        pytest.param(EASY_MAX_SCORE + 1e-9, Tier.MEDIUM, id="just-above-easy"),
        pytest.param(50.0, Tier.MEDIUM, id="inside-medium"),
        pytest.param(MEDIUM_MAX_SCORE, Tier.MEDIUM, id="medium-cutoff-is-medium"),
        pytest.param(MEDIUM_MAX_SCORE + 1e-9, Tier.HARD, id="just-above-medium"),
        pytest.param(99.0, Tier.HARD, id="inside-hard"),
        pytest.param(SCORE_MAX, Tier.HARD, id="ceiling-of-the-scale"),
    ],
)
def test_a_score_lands_in_the_band_adr_0005_puts_it_in(
    score: float, expected: Tier
) -> None:
    """The classifier itself, at both cutoffs and on both sides of each.

    The two boundary values are the point: ADR-0005 writes the bands as
    ``[0, 33]``, ``(33, 66]``, ``(66, 100]``, so a cutoff belongs to the band
    *below* it. An implementation that used ``<`` instead of ``<=`` would pass
    every "inside" case here and fail exactly these two.
    """
    # Through ``classify`` with a zero branch count, because that is the only
    # way a caller can ask: ADR-0025 makes a score alone insufficient to
    # classify, and ``tier_for_score`` is private for exactly that reason.
    assert classify(score, 0) is expected


def test_classification_and_the_band_table_never_disagree() -> None:
    """The two derivations of one rule, cross-checked across the whole scale.

    ``classify`` compares against the cutoffs; ``TIER_BANDS`` lays them out as
    intervals. Both come from :data:`EASY_MAX_SCORE` and
    :data:`MEDIUM_MAX_SCORE`, and this is what holds them to it: for a thousand
    scores spanning the scale, the tier the classifier reports is the one whose
    band contains the score, reading ``low < score <= high`` (with the floor
    included in the lowest band).

    Every call passes ``branch_nodes=0``, which is not incidental: the band
    table describes the three score-band tiers, and ``Tier.GUESS`` is outside
    that description entirely (ADR-0025). A classifier that let a branch count
    of zero reach ``GUESS`` would fail the band lookup below with a
    ``KeyError``, which is a better failure than a wrong tier.
    """
    steps = 1000
    for step in range(steps + 1):
        score = SCORE_MIN + (SCORE_MAX - SCORE_MIN) * step / steps
        tier = classify(score, 0)
        low, high = TIER_BANDS[tier]
        assert low <= score <= high
        assert (score > low) or (tier is Tier.EASY and score == SCORE_MIN)
        # No other band claims it.
        assert [
            other
            for other in (Tier.EASY, Tier.MEDIUM, Tier.HARD)
            if TIER_BANDS[other][0] <= score <= TIER_BANDS[other][1]
            and classify(score, 0) is other
        ] == [tier]


@pytest.mark.parametrize("tier", list(Tier))
def test_a_tier_is_its_flag_value_and_carries_a_display_label(tier: Tier) -> None:
    """FR-008's four tiers, in the two spellings the tool needs.

    ``str`` value = what ``--difficulty`` takes; :attr:`Tier.label` = the
    capitalized form AC-020 writes ("Medium"). One type, so the flag value and
    the display name cannot drift.
    """
    assert isinstance(tier, str)
    assert tier.value == tier.value.lower()
    assert tier.label == tier.value.capitalize()


def test_the_tool_supports_exactly_the_four_tiers_adr_0025_names() -> None:
    """FR-008 named three tiers; ADR-0025 (DEC-030) added ``guess`` as a fourth.

    The *values* are asserted and not just the count, because the value is the
    contract: it is what a user types, what an export payload carries, what a
    PDF filename is built from and what a DB row stores. ``Tier.label`` is
    presentational and ADR-0025 says outright that "Guess" may be renamed later
    without any of that moving.
    """
    assert [tier.value for tier in Tier] == ["easy", "medium", "hard", "guess"]


def test_only_three_of_the_four_tiers_are_score_bands() -> None:
    """ADR-0025's Negative, as a property of the band table.

    ``Tier.GUESS`` is keyed on the solve's ``branch_nodes``, not on a number
    (EC-015), so it has no band — and :attr:`Tier.band` says so with ``None``
    rather than with a fabricated range. A band table that carried a fourth
    entry would be the first place somebody re-derived the tier from a score,
    which is precisely what the fourth tier exists to prevent.
    """
    assert set(TIER_BANDS) == {Tier.EASY, Tier.MEDIUM, Tier.HARD}
    assert Tier.GUESS.band is None
    for tier in (Tier.EASY, Tier.MEDIUM, Tier.HARD):
        assert tier.band == TIER_BANDS[tier]


@pytest.mark.parametrize("score", [SCORE_MIN, 10.0, EASY_MAX_SCORE, 50.0, SCORE_MAX])
def test_no_score_whatsoever_classifies_guess(score: float) -> None:
    """The band half of the classifier can never reach the fourth tier.

    EC-015 keys ``GUESS`` on a solve fact, so there is no number — not the top
    of the scale, not one past it — that a line-solvable puzzle can score and
    be called Guess for. This is AC-121 stated at the classifier rather than at
    the scorer.
    """
    assert classify(score, 0) is not Tier.GUESS
    assert classify(score * 10, 0) is not Tier.GUESS
    assert classify(-score, 0) is not Tier.GUESS


# --------------------------------------------------------------------------
# AC-021 — TestSelectDifficulty_RejectsUnknownTier
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Extreme", id="ac-021-extreme"),
        pytest.param("extreme", id="lowercased-extreme"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace-only"),
        pytest.param("easyish", id="near-miss"),
        pytest.param("EASY MEDIUM", id="two-tiers"),
        pytest.param("0", id="a-raw-score"),
    ],
)
def test_rejects_unknown_tier(text: str) -> None:
    """AC-021: a difficulty that is not a supported tier is refused.

    A domain error, raised by a pure function with no argv anywhere in sight —
    which is the point of ADR-0010: the rule is testable without the parser,
    because the parser does not hold it.
    """
    with pytest.raises(UnsupportedDifficulty) as excinfo:
        parse_tier(text)

    message = str(excinfo.value)
    assert repr(text) in message
    # The user's next move is to pick a tier that does exist, so the message
    # has to name them.
    for tier in Tier:
        assert tier.value in message


def test_rejects_unknown_tier_before_anything_is_generated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-021 end to end: the request is rejected, not a candidate.

    "The request is rejected" means nothing was sourced, solved or scored — so
    a source that fails the test if it is ever called is the assertion.
    """

    def unreachable(*args: object, **kwargs: object) -> object:
        raise AssertionError("an unsupported tier must be refused before sourcing")

    monkeypatch.setattr(orchestrator.sourcing, "for_mode", unreachable)

    with pytest.raises(UnsupportedDifficulty):
        orchestrator.generate(
            GenerationRequest(mode="random", width=10, height=10, density=50, seed=0,
                              difficulty="Extreme")
        )


def test_an_unknown_tier_is_a_domain_error_and_not_an_argparse_usage_error() -> None:
    """Guardrail G-4 / ADR-0010: no ``choices=`` shortcut for AC-021.

    Two halves of one rule. The parser must *accept* the string (a ``choices=``
    would have raised SystemExit(2) here), and the tool must then refuse it
    with its own message on stderr and INVALID_INPUT — the exit code the other
    "you asked for something that does not exist" errors use.
    """
    args = cli.build_parser().parse_args(["generate", "--difficulty", "extreme"])
    assert args.difficulty == "extreme"


def test_an_unknown_tier_reaches_the_user_as_exit_code_three(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["generate", "--size", "10", "--difficulty", "Extreme"])

    assert exit_code == cli.ExitCode.INVALID_INPUT
    captured = capsys.readouterr()
    assert "Extreme" in captured.err
    assert captured.out == ""


# --------------------------------------------------------------------------
# AC-020 — TestSelectDifficulty_AcceptsValidTier
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("easy", Tier.EASY, id="easy"),
        pytest.param("medium", Tier.MEDIUM, id="medium"),
        pytest.param("hard", Tier.HARD, id="hard"),
        # AC-020 (re-worded): ADR-0025's fourth tier is a legitimate request,
        # not a value the domain refuses. Whether the generator can *satisfy*
        # it is POL-004's business and a different test.
        pytest.param("guess", Tier.GUESS, id="guess"),
        pytest.param("Guess", Tier.GUESS, id="ac-020-capitalized-guess"),
        # AC-020 writes the tier as "Medium"; the flag takes "medium". Both are
        # the same tier, and neither spelling is the user's mistake to fix.
        pytest.param("Medium", Tier.MEDIUM, id="ac-020-capitalized"),
        pytest.param("HARD", Tier.HARD, id="shouted"),
        pytest.param("  easy  ", Tier.EASY, id="padded"),
    ],
)
def test_accepts_valid_tier(text: str, expected: Tier) -> None:
    assert parse_tier(text) is expected


def test_accepts_valid_tier_and_tags_the_aggregate_pending_confirmation() -> None:
    """AC-020: a request for "Medium" produces a puzzle tagged "Medium".

    "Pending score confirmation" is the second half of the criterion and the
    reason ``requested_tier`` and ``difficulty_tier`` are two different
    attributes: at creation the aggregate carries what was *asked for*, and
    carries no score at all — nothing has been generated, so nothing has been
    confirmed.
    """
    request = GenerationRequest(
        mode="random", width=10, height=10, density=50, difficulty="Medium"
    )

    puzzle = Puzzle(
        request=request, seed=0, requested_tier=parse_tier(request.difficulty or "")
    )

    assert puzzle.requested_tier is Tier.MEDIUM
    assert puzzle.requested_tier is not None
    assert puzzle.requested_tier.label == "Medium"
    # Pending: no candidate, no score, no confirmed tier yet.
    assert puzzle.difficulty_score is None
    assert puzzle.difficulty_tier is None
    assert puzzle.ready_for_export is False


def test_a_generated_puzzle_carries_the_tier_it_was_asked_for() -> None:
    """AC-020 through the real pipeline (pinned seed).

    At 10x10 / 50% density, seed 0's first candidate is unique and — being a
    small grid a line solver walks straight through — scores in the Easy band,
    so this run needs neither a regenerate nor a resample. What it shows is the
    tag surviving the whole trip: the tier on the returned aggregate is the one
    the request named, not one derived from the score.
    """
    puzzle = orchestrator.generate(
        GenerationRequest(
            mode="random", width=10, height=10, density=50, seed=0, difficulty="easy"
        )
    )

    assert puzzle.requested_tier is Tier.EASY
    assert puzzle.difficulty_score is not None
    assert puzzle.difficulty_tier is Tier.EASY
    assert puzzle.ready_for_export is True


def test_no_difficulty_flag_leaves_the_tier_unset_rather_than_easy() -> None:
    """``None`` is "no tier requested", which is not the same as "Easy".

    The distinction is what keeps POL-004 off for a run that never asked for a
    tier: an unset tier accepts any score, whereas ``Tier.EASY`` would discard
    every candidate that scored above 33.
    """
    puzzle = orchestrator.generate(
        GenerationRequest(mode="random", width=10, height=10, density=50, seed=0)
    )

    assert puzzle.request.difficulty is None
    assert puzzle.requested_tier is None
    # Scored all the same — the score is FR-009's, not FR-008's, and CARD-014's
    # PDF header needs one whether or not a tier was asked for.
    assert puzzle.difficulty_score is not None
    assert puzzle.difficulty_tier is not None


# --------------------------------------------------------------------------
# The flag, at the adapter boundary
# --------------------------------------------------------------------------


def test_the_flag_is_carried_inward_exactly_as_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COMP-001 translates, it does not judge (ADR-0010).

    Whatever the user typed reaches ``GenerationRequest.difficulty`` unchanged
    — no normalization, no rejection, no default — because the tier rule lives
    inward of here.
    """
    seen: list[GenerationRequest] = []

    def fake_generate(request: GenerationRequest) -> Puzzle:
        seen.append(request)
        return Puzzle(request=request, seed=0)

    monkeypatch.setattr(orchestrator, "generate", fake_generate)
    monkeypatch.setattr(orchestrator, "export_puzzle", lambda puzzle: ())

    assert cli.main(["generate", "--difficulty", "Extreme"]) == cli.ExitCode.OK
    assert cli.main(["generate"]) == cli.ExitCode.OK

    assert [request.difficulty for request in seen] == ["Extreme", None]


def test_the_help_lists_the_tiers_that_actually_exist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--help`` reads the tier vocabulary from the domain, like ``--export``.

    Listing them is a documentation choice, not validation — the flag still has
    no ``choices=`` — but a hand-written list could drift from what
    ``parse_tier`` accepts, and a user reading a stale ``--help`` would be told
    to type a tier that gets refused.
    """
    with pytest.raises(SystemExit):
        cli.main(["generate", "--help"])

    out = capsys.readouterr().out
    assert "--difficulty" in out
    for tier in difficulty.Tier:
        assert tier.value in out


# --------------------------------------------------------------------------
# EC(ADR-0025/R2) — exactly one tier classifier in the package
# --------------------------------------------------------------------------

#: The package on disk, walked rather than imported, the same way
#: ``tests/test_cli.py``'s ADR-0007 import guard does it — so a module a later
#: card adds is covered from the moment it lands and this test never has to be
#: edited to keep the rule enforced.
_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "nonogram"
if not _PACKAGE_DIR.is_dir():  # pragma: no cover - installed-only checkout
    _PACKAGE_DIR = Path(difficulty.__file__).parent

#: The module ADR-0025/R2 puts the one classifier in. Matched by *path* and not
#: by basename, so a second ``difficulty.py`` somewhere under the package (an
#: ``admin/difficulty.py``, say) would be walked like every other module rather
#: than exempted by its name — which is precisely the shape ADR-0025/R2 forbids.
_CLASSIFIER_MODULE = _PACKAGE_DIR / "difficulty.py"

#: Names that would mean "this module is deciding a tier for itself". The two
#: cutoffs are the score half of the rule; ``branch_nodes`` is the solve-fact
#: half, and EC-015 is precisely the claim that no second module may read it to
#: reach a tier.
_CUTOFF_NAMES = frozenset({"EASY_MAX_SCORE", "MEDIUM_MAX_SCORE"})
_SOLVE_FACT = "branch_nodes"


def _tier_deciding_offences(path: Path) -> list[str]:
    """Places in one source file that decide a tier without asking COMP-006.

    Two shapes are looked for, both as ``ast`` rather than as text so that a
    comment or a docstring mentioning a cutoff is not an offence:

    * a comparison against one of the cutoff constants — the score half;
    * a comparison of a ``branch_nodes`` attribute or name against a *number* —
      the EC-015 half, which is what ``admin/image_to_puzzle`` used to do with
      a grid size and what any module could start doing with the real fact.

    Reading ``branch_nodes`` is not itself an offence: the orchestrator has to
    carry it from the solve to the classifier, and this file's own fixtures
    pass it around. *Comparing it to a count* is, because that comparison is
    the rule EC-015 reserves to one place.

    Two exclusions, both narrow and both necessary. ``branch_nodes is None``
    asks "has this candidate been judged yet", which every carrier of the value
    must be able to ask and which no tier depends on — so ``is``/``is not`` and
    the ``None`` literal are not counted. And the numeric test is on the
    literal's *type*, not on the operator, so ``> 0``, ``>= 1`` and ``== 0``
    are all caught while a nullability check is not.
    """
    offences: list[str] = []
    with warnings.catch_warnings():
        # The package carries ASCII-art docstrings with backslashes in them
        # (``sourcing/templates/``), which ``ast.parse`` flags. Not this rule's
        # business, and not worth a line of noise per run.
        warnings.simplefilter("ignore", SyntaxWarning)
        tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for operand in operands:
            if isinstance(operand, ast.Name) and operand.id in _CUTOFF_NAMES:
                offences.append(f"{path.name}:{node.lineno} compares against {operand.id}")
            if isinstance(operand, ast.Attribute) and operand.attr in _CUTOFF_NAMES:
                offences.append(f"{path.name}:{node.lineno} compares against {operand.attr}")
        reads_branch_nodes = any(
            (isinstance(operand, ast.Attribute) and operand.attr == _SOLVE_FACT)
            or (isinstance(operand, ast.Name) and operand.id == _SOLVE_FACT)
            for operand in operands
        )
        against_a_count = any(
            isinstance(operand, ast.Constant)
            and isinstance(operand.value, (int, float))
            and not isinstance(operand.value, bool)
            for operand in operands
        )
        if reads_branch_nodes and against_a_count:
            offences.append(
                f"{path.name}:{node.lineno} compares {_SOLVE_FACT} against a count"
            )
    return offences


def test_no_module_but_difficulty_classifies_a_tier() -> None:
    """EC(ADR-0025/R2) — there is exactly one tier classifier, and it is COMP-006's.

    ADR-0025 broke ADR-0005's "a tier is a score band" model for one member, so
    the cost of a *second* classifier went up: a module that compared a score
    against the cutoffs itself would now be silently wrong for every branching
    puzzle, not merely duplicated. And a retune of the cutoffs would move the
    bands without moving that module's classification with them.

    Walked over the package on disk, so a module no card has written yet is
    covered the moment it lands — the same arrangement, and the same reasoning,
    as ``tests/test_cli.py``'s ADR-0007 import guard.
    """
    offences = [
        offence
        for path in sorted(_PACKAGE_DIR.rglob("*.py"))
        if path != _CLASSIFIER_MODULE
        for offence in _tier_deciding_offences(path)
    ]

    assert _CLASSIFIER_MODULE.is_file(), (
        "the one exempted module is supposed to be COMP-006 itself; if it moved, "
        "this guard has been exempting nothing and passing vacuously"
    )
    assert offences == [], (
        "ADR-0025/R2 violation — these modules decide a tier instead of asking "
        f"difficulty.classify: {offences}"
    )


def test_the_rule_catches_a_module_that_started_classifying(tmp_path: Path) -> None:
    """Guard the guard: the walk above passes vacuously if the rule is broken.

    Both shapes, in one fabricated module — the score comparison and the
    ``branch_nodes`` comparison — because each is a separate way of getting to
    the same wrong answer and a rule that only caught one would leave the
    other's door open. ``admin/image_to_puzzle.create_puzzle_from_image``, the
    real instance this card retired, was a third shape again (a *size*
    comparison), which is why the rule is stated over the inputs a tier may
    legitimately be derived from rather than over a list of bad formulas.
    """
    offending = tmp_path / "__tier_guard_probe__.py"
    offending.write_text(
        "from nonogram.difficulty import EASY_MAX_SCORE\n"
        "\n"
        "def tier(score, signals):\n"
        "    if score <= EASY_MAX_SCORE:\n"
        "        return 'easy'\n"
        "    if signals.branch_nodes > 0:\n"
        "        return 'guess'\n"
        "    return 'hard'\n",
        encoding="utf-8",
    )
    try:
        offences = _tier_deciding_offences(offending)
    finally:
        offending.unlink()

    assert len(offences) == 2
    assert any("EASY_MAX_SCORE" in offence for offence in offences)
    assert any("branch_nodes" in offence for offence in offences)


def test_the_rule_leaves_the_legitimate_shapes_alone(tmp_path: Path) -> None:
    """...and does not fire on carrying the facts to the classifier.

    The orchestrator reads ``branch_nodes`` off the solve and hands it to
    ``classify``; a caller stores it; a test builds a record with it. None of
    those is a decision, and a rule that forbade *touching* the number would
    make ADR-0025/R2 unimplementable — the one classifier has to be given its
    inputs by somebody.
    """
    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        "from nonogram import difficulty\n"
        "\n"
        "def judge(score, signals):\n"
        "    return difficulty.classify(score, signals.branch_nodes)\n"
        "\n"
        "def record(puzzle, signals):\n"
        "    puzzle.branch_nodes = signals.branch_nodes\n"
        "\n"
        "def describe(tier):\n"
        "    return tier is difficulty.Tier.GUESS\n",
        encoding="utf-8",
    )

    assert _tier_deciding_offences(allowed) == []


# --------------------------------------------------------------------------
# AC-020 (re-worded) — `guess` is a request the pipeline tries to satisfy
# --------------------------------------------------------------------------


def test_requesting_the_fourth_tier_is_a_generation_outcome_not_a_rejection() -> None:
    """ADR-0025: "requesting ``guess`` is a legitimate request the loop can satisfy".

    The distinction this pins is between *refusing the request* and *failing to
    fill it*. ``--difficulty guess`` parses, reaches the domain and drives
    POL-004's loop like any other tier; what comes back is
    ``GenerationAbandoned`` — the resample bound, reported with the tier named —
    and not ``UnsupportedDifficulty``.

    That outcome is the measured state of the source rather than a property of
    the tier: no generated puzzle has ever needed a real branch (0 of 6,620 in
    ADR-0029's sweep, 0 of 462 in CARD-076's), so the loop exhausts its budget.
    If a source ever produces a branching grid this test starts returning a
    puzzle instead, and the right response is to say so rather than to keep the
    exhaustion pinned.
    """
    with pytest.raises(GenerationAbandoned) as excinfo:
        orchestrator.generate(
            GenerationRequest(
                mode="random", width=10, height=10, density=50, seed=3,
                difficulty="guess",
            )
        )

    message = str(excinfo.value)
    assert Tier.GUESS.label in message
    # The message describes the tier by the fact that defines it, because it
    # has no band on the 0-100 scale to point the user at (ADR-0025).
    assert "branch" in message


# --------------------------------------------------------------------------
# ADR-0025's Negative — every Tier consumer handles the fourth member
# --------------------------------------------------------------------------

#: The admin panel's templates, read as source. The two surfaces below are
#: Jinja and cannot be reached from ``difficulty.Tier`` the way the CLI's help
#: and the web form's options are, so they are the two places a fourth enum
#: member could be silently dropped — which is exactly why they are asserted.
_ADMIN_TEMPLATES = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "nonogram"
    / "admin"
    / "templates"
)


def test_the_admin_puzzle_list_gives_the_fourth_tier_a_badge_of_its_own() -> None:
    """ADR-0025's Negative, at the admin review's tier badge.

    ``Guess`` is not "a harder Hard": it is the one tier that is not a score
    band at all. The badge had an ``{% if Easy %}{% elif Medium %}{% else %}``
    chain, so before this card a Guess row would have rendered in Hard's colour
    and a reviewer scanning the list could not have told the two apart — the
    single most consequential confusion the fourth tier exists to prevent.

    Also asserted: the comparison is case-insensitive. A row written through
    the generation pipeline stores the enum *value* (``"hard"``) while an older
    row stores the display label (``"Hard"``), and the badge has to colour both
    — re-grading or rewriting those rows is CARD-077's, not this template's.
    """
    source = (_ADMIN_TEMPLATES / "puzzles_list.html").read_text(encoding="utf-8")

    for tier in Tier:
        assert f"== '{tier.value}'" in source, tier
    assert "difficulty_tier|lower" in source
    # A colour of its own, not Hard's.
    assert "#8e44ad" in source


def test_the_admin_puzzle_filter_offers_the_fourth_tier() -> None:
    """The same Negative at the tier *filter*: an unofferable tier is unreachable.

    The filter itself is a plain equality on the stored string and is unchanged
    by this card; what is asserted is that a reviewer can ask for the fourth
    tier at all. (The admin *strategy* filter is CARD-072's and is deliberately
    not touched here.)
    """
    source = (_ADMIN_TEMPLATES / "puzzles_list.html").read_text(encoding="utf-8")

    for tier in Tier:
        assert f'<option value="{tier.label}"' in source, tier


def test_the_cli_help_names_the_fourth_tier_and_says_what_it_means() -> None:
    """``--difficulty``'s help is read off the enum, so ``guess`` arrived for free.

    The half that did *not* arrive for free is the explanation. Four tier names
    in a list tell a user nothing about why one of them is not a difficulty in
    the ordinary sense, and "which tiers exist" is the question the help exists
    to answer (AC-021's message answers "which did you mean"). So the help
    says what the three bands grade and what the fourth is keyed on.
    """
    parser = cli.build_parser()
    help_text = parser.format_help()
    generate_help = [
        action.help or ""
        for action in parser._subparsers._group_actions[0].choices["generate"]._actions
        if action.dest == "difficulty"
    ]

    assert generate_help, "--difficulty is gone from the generate subcommand"
    text = generate_help[0]
    for tier in Tier:
        assert tier.value in text, tier
    assert "guess" in text and "branch" in text
    assert help_text  # the top-level parser still builds


# --------------------------------------------------------------------------
# tier_of_record — reading a tier back out of text that already exists
# (CARD-076 review, finding F-002)
# --------------------------------------------------------------------------


def test_both_spellings_of_every_tier_read_back_to_the_same_member() -> None:
    """The whole point: value and label are one tier, not two.

    A row written through the generation pipeline stores the enum *value*,
    because ``orchestrator.Puzzle.difficulty_tier`` is a ``Tier`` and a
    ``StrEnum``'s ``str`` is its value; older and hand-entered rows carry the
    display label. Four admin surfaces compared against the label only and so
    counted none of the pipeline's own rows — the defect this function exists
    to make unrepeatable.
    """
    for tier in Tier:
        assert tier_of_record(tier.value) is tier
        assert tier_of_record(tier.label) is tier
        assert tier_of_record(tier.value.upper()) is tier
        assert tier_of_record(f"  {tier.label}  ") is tier


def test_guess_reads_back_like_every_other_tier() -> None:
    """ADR-0025's fourth member is not a special case for the reader."""
    assert tier_of_record("guess") is Tier.GUESS
    assert tier_of_record("Guess") is Tier.GUESS


@pytest.mark.parametrize(
    "value", [None, "", "   ", "extreme", "Easyish", 5, 33.0, object(), b"easy"]
)
def test_anything_that_is_not_a_tier_reads_back_as_none(value: object) -> None:
    """Total, and never raising, is the contract that separates it from parse_tier.

    ``parse_tier`` rejects loudly because a user typed the word and needs to be
    told (AC-021). This one reads text that already exists — a stored row, a
    query string — where there is nobody to tell and raising would turn a bad
    row into a 500.
    """
    assert tier_of_record(value) is None


def test_it_does_not_become_a_second_classifier() -> None:
    """It reads a tier that was already decided; it never decides one.

    ADR-0025/R2 allows exactly one classifier. ``tier_of_record`` takes text,
    not a score and not a branch count, so it cannot be handed the inputs a
    classification is made from — which is why the ast guard above passes with
    it in the package and would not if it took a score.
    """
    signature = inspect.signature(tier_of_record)
    assert list(signature.parameters) == ["value"]
    source = inspect.getsource(tier_of_record)
    assert "branch_nodes" not in source
    assert "EASY_MAX_SCORE" not in source
    assert "MEDIUM_MAX_SCORE" not in source
