"""COMP-006/COMP-001 tests: FR-008's tier selector and ADR-0005's cutoffs.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-020  TestSelectDifficulty_AcceptsValidTier  -> test_accepts_valid_tier*
    AC-021  TestSelectDifficulty_RejectsUnknownTier -> test_rejects_unknown_tier*

CARD-098's four (the Guess tier retired) — same convention, added by CARD-071
because the labels were cited in the registry without ever being written down
beside the functions, which reads to the validator as a dead link:

    ADR-0031/R1  TestTiers_ThreeBandsAndNoFourthTier
                 -> test_tiers_three_bands_and_no_fourth_tier
    AC-174 (FR-026), ADR-0031/R2  TestTiers_BranchingIsAStrategyNotATier
                 -> test_tiers_branching_is_a_strategy_not_a_tier
    ADR-0031/R3  TestTiers_LegacyGuessRowReadsAsHard
                 -> test_tiers_legacy_guess_row_reads_as_hard
    CARD-098 AC-4  TestTiers_GuessIsNoLongerARequestableTier
                 -> test_tiers_guess_is_no_longer_a_requestable_tier

Two halves, matching the two things "a tier" has to be.

*The bands* (``nonogram.difficulty``): ADR-0005 splits the 0..100 scale into
three bands with two tunable constants, and the tests below pin the cutoffs,
the ends they belong to, and — the one that matters most for a tunable table —
that the bands and the classifier are derived from the same two constants, so
moving a cutoff moves both together. A test that restated the cutoff figures as
its own expectation would only be pinning the current tuning; these pin the
*structure* and check the numbers once, against the decisions directly.

The figures were ADR-0005's equal tertiles (33/66) until CARD-137 moved the
medium/hard cutoff to ``90.0`` on the owner's decision; the split is no longer
equal, and the tier bands are no longer the ladder's rung bands
(``tests/test_difficulty.py`` holds that second table).

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
from jinja2 import Environment, FileSystemLoader

from nonogram import cli, difficulty, orchestrator, solver
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


def test_the_scale_is_split_where_adr_0005_and_card_137_put_the_cutoffs() -> None:
    """Easy [0, 33], Medium (33, 90], Hard (90, 100].

    The one place the literal numbers are asserted. Everything else in this
    module reads them from the module, so a retune moves one test rather than a
    dozen — which is what makes the table tunable in practice and not just in
    principle.

    **``33.0`` is ADR-0005's and has never moved.** It coincides with the top
    of the ladder's bottom rung, which is what keeps Easy meaning exactly "the
    overlap rule finished it" (ADR-0029, History 2026-09-13).

    **``90.0`` is CARD-137's**, and it is the recalibration ADR-0005 has been
    owed since ADR-0029. At ``66.0`` the cutoff coincided with the other rung
    boundary, so Medium meant "topped out at ``line_dp``" — an accident of a
    random draw that the owner measured at 5 puzzles in 300 on production.
    ``90.0`` coincides with nothing on the ladder: it cuts the
    ``probe_contradiction`` rung at ``(90 - 66) / 34`` = 70.6% of the grid, so
    Medium is "a little non-trivial work" and Hard is "a lot". No stored grade
    moves, because the score mapping is the *rung* table and that is untouched
    — see ``tests/test_difficulty.py`` and ``difficulty.RUNG_BANDS``.
    """
    assert EASY_MAX_SCORE == 33.0
    assert MEDIUM_MAX_SCORE == 90.0
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

    The two boundary values are the point: ADR-0005 writes the bands with
    *inclusive* upper bounds — ``[0, 33]``, ``(33, 90]``, ``(90, 100]`` as the
    cutoffs stand — so a cutoff belongs to the band *below* it. An
    implementation that used ``<`` instead of ``<=`` would pass every "inside"
    case here and fail exactly these two.
    """
    # Through ``classify`` with a zero branch count, because that is the only
    # way a caller can ask: ADR-0025 makes a score alone insufficient to
    # classify, and ``tier_for_score`` is private for exactly that reason.
    assert classify(score) is expected


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
        tier = classify(score)
        low, high = TIER_BANDS[tier]
        assert low <= score <= high
        assert (score > low) or (tier is Tier.EASY and score == SCORE_MIN)
        # No other band claims it.
        assert [
            other
            for other in (Tier.EASY, Tier.MEDIUM, Tier.HARD)
            if TIER_BANDS[other][0] <= score <= TIER_BANDS[other][1]
            and classify(score) is other
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
    assert [tier.value for tier in Tier] == ["easy", "medium", "hard"]


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

    One shape is looked for, as ``ast`` rather than as text so that a comment
    or a docstring mentioning a cutoff is not an offence: **a comparison
    against one of the cutoff constants.** A module that did that would be a
    second band table, silently left behind by the next retune.

    Until CARD-098 a second shape counted too — comparing ``branch_nodes``
    against a number — because ADR-0025 made a branching solve a *tier* and
    reserved that comparison to COMP-006. ADR-0031 retired the tier, so the
    comparison now decides a **strategy** rather than a difficulty, and three
    modules do it on purpose (the orchestrator and the admin's two readers).
    Keeping the rule would have meant three permanent exemptions to a guard
    whose whole value is having none.
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

    The score comparison, in a fabricated module. ``branch_nodes`` used to be
    a second shape here; CARD-098 retired the tier that made it one, and the
    guard with it — see :func:`_tier_deciding_offences`.
    """
    offending = tmp_path / "__tier_guard_probe__.py"
    offending.write_text(
        "from nonogram.difficulty import EASY_MAX_SCORE\n"
        "\n"
        "def tier(score, signals):\n"
        "    if score <= EASY_MAX_SCORE:\n"
        "        return 'easy'\n"
        "    return 'hard'\n",
        encoding="utf-8",
    )
    try:
        offences = _tier_deciding_offences(offending)
    finally:
        offending.unlink()

    assert len(offences) == 1
    assert any("EASY_MAX_SCORE" in offence for offence in offences)


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
        "    return difficulty.classify(score)\n"
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


# --------------------------------------------------------------------------
# CARD-098 — the Guess tier retired
#
# The scale is three bands again. `guess` is not gone from the system: it
# survives as a *strategy*, because "this solve had to branch" is still true
# of a puzzle and still worth printing beside it. What goes is the claim that
# it is a difficulty, which no measurement ever supported — 0 of 6,620
# (ADR-0029), 0 of 462 (CARD-076), 0 of 16 stored rows, and CARD-072's finding
# that no random draw in the supported range branches at all.
# --------------------------------------------------------------------------


def test_tiers_three_bands_and_no_fourth_tier() -> None:
    """AC-1: three members, and every one of them is a score band.

    The fourth tier was the only member with no band — ``band`` answered
    ``None`` for it, and ``classify`` needed a second argument to reach it.
    Both of those are gone with it, which is the real simplification: a tier
    is once again *nothing but* a bucket on the 0..100 scale.
    """
    assert [tier.value for tier in difficulty.Tier] == ["easy", "medium", "hard"]
    assert all(tier.band is not None for tier in difficulty.Tier)
    assert not hasattr(difficulty.Tier, "GUESS")

    assert list(inspect.signature(difficulty.classify).parameters) == ["score"]
    for score in (0.0, 0.1, 33.0, 33.1, 66.0, 66.1, 99.9, 100.0):
        assert difficulty.classify(score) in set(difficulty.Tier)


def test_tiers_branching_is_a_strategy_not_a_tier() -> None:
    """AC-2: a branching solve keeps ``guess`` among its strategies.

    This is the whole of what replaces the tier, and it is why retiring one
    does not lose the fact. The tier such a puzzle gets is simply whichever
    band its score falls in — a branching puzzle is no longer *defined* as the
    hardest thing, it is scored like everything else.
    """
    puzzle = orchestrator.generate(
        GenerationRequest(mode="random", width=10, height=10, density=40, seed=7)
    )
    ladder = ("simple_overlap", "line_dp")

    puzzle.record_difficulty(12.0, 1, ladder)
    assert puzzle.strategies == (*ladder, solver.STRATEGY_GUESS)
    assert puzzle.difficulty_tier is difficulty.classify(12.0)

    puzzle.record_difficulty(12.0, 0, ladder)
    assert puzzle.strategies == ladder
    assert puzzle.difficulty_tier is difficulty.classify(12.0)


def test_tiers_legacy_guess_row_reads_as_hard() -> None:
    """AC-3: a row written before this card still reads, and reads as Hard.

    ``tier_of_record`` is the *output* rule — text that already exists and
    cannot be argued with. A stored ``"guess"`` is such text: this project's
    own database has none, but the production one has not been checked and
    must not be (CARD-077 G-1), so the reader carries the mapping regardless.

    Hard rather than ``None``, because ``None`` is "not a tier at all" and
    would drop the row out of counts and filters silently. A puzzle that
    needed a branch is at least as hard as the hardest band, so Hard is the
    nearest true statement about it — and a re-grade will reassign it on its
    own terms.
    """
    for spelling in ("guess", "Guess", "GUESS", " guess "):
        assert difficulty.tier_of_record(spelling) is difficulty.Tier.HARD, spelling

    # Still not a tier anyone can *ask* for, and still nothing at all when the
    # text is not a tier.
    assert difficulty.tier_of_record("extreme") is None


def test_tiers_guess_is_no_longer_a_requestable_tier(tmp_path) -> None:
    """AC-4: ``--difficulty guess`` is refused like any other unknown word.

    The input rule and the output rule part company here, deliberately: a
    stored ``guess`` is history and is read (above), while a *request* for one
    is a user asking for something this build does not have, and AC-021 says
    they are told.
    """
    with pytest.raises(UnsupportedDifficulty) as excinfo:
        difficulty.parse_tier("guess")

    message = str(excinfo.value)
    assert "guess" in message
    assert "easy" in message and "medium" in message and "hard" in message

    exit_code = cli.main(
        [
            "generate", "--mode", "random", "--size", "10", "--density", "40",
            "--difficulty", "guess", "--out", str(tmp_path),
        ]
    )
    assert exit_code == cli.ExitCode.INVALID_INPUT
