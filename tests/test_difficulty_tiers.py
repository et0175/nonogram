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

import itertools

import pytest

from nonogram import cli, difficulty, orchestrator
from nonogram.difficulty import (
    EASY_MAX_SCORE,
    MEDIUM_MAX_SCORE,
    SCORE_MAX,
    SCORE_MIN,
    TIER_BANDS,
    Tier,
    parse_tier,
    tier_for_score,
)
from nonogram.errors import UnsupportedDifficulty
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
    bands = [TIER_BANDS[tier] for tier in Tier]
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
    assert tier_for_score(score) is expected


def test_classification_and_the_band_table_never_disagree() -> None:
    """The two derivations of one rule, cross-checked across the whole scale.

    ``tier_for_score`` compares against the cutoffs; ``TIER_BANDS`` lays them
    out as intervals. Both come from :data:`EASY_MAX_SCORE` and
    :data:`MEDIUM_MAX_SCORE`, and this is what holds them to it: for a thousand
    scores spanning the scale, the tier the classifier reports is the one whose
    band contains the score, reading ``low < score <= high`` (with the floor
    included in the lowest band).
    """
    steps = 1000
    for step in range(steps + 1):
        score = SCORE_MIN + (SCORE_MAX - SCORE_MIN) * step / steps
        tier = tier_for_score(score)
        low, high = TIER_BANDS[tier]
        assert low <= score <= high
        assert (score > low) or (tier is Tier.EASY and score == SCORE_MIN)
        # ``Tier.contains`` is the caller-facing form of the same question.
        assert tier.contains(score)
        assert [other for other in Tier if other.contains(score)] == [tier]


@pytest.mark.parametrize("tier", list(Tier))
def test_a_tier_is_its_flag_value_and_carries_a_display_label(tier: Tier) -> None:
    """FR-008's three tiers, in the two spellings the tool needs.

    ``str`` value = what ``--difficulty`` takes; :attr:`Tier.label` = the
    capitalized form AC-020 writes ("Medium"). One type, so the flag value and
    the display name cannot drift.
    """
    assert isinstance(tier, str)
    assert tier.value == tier.value.lower()
    assert tier.label == tier.value.capitalize()


def test_the_tool_supports_exactly_easy_medium_and_hard() -> None:
    """FR-008 names three tiers; a fourth would need an ADR-0005 revision."""
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
            GenerationRequest(mode="random", size=10, density=50, seed=0,
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
    request = GenerationRequest(mode="random", size=10, density=50, difficulty="Medium")

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
        GenerationRequest(mode="random", size=10, density=50, seed=0, difficulty="easy")
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
        GenerationRequest(mode="random", size=10, density=50, seed=0)
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
