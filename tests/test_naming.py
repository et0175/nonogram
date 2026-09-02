"""COMP-002/COMP-001 tests: FR-015's puzzle name, and the file it names.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-042  TestPuzzleName_AutoGeneratesModeTimestampForRandomMode
                -> test_puzzle_name_auto_generates_mode_timestamp_for_random_mode*
    AC-043  TestPuzzleName_AutoGeneratesFromLibraryKey
                -> test_puzzle_name_auto_generates_from_library_key*
    AC-044  TestPuzzleName_OverrideViaFlag
                -> test_puzzle_name_override_via_flag*
    AC-045  TestPuzzleName_RejectsEmptyName
                -> test_puzzle_name_rejects_empty_name*

Three things shape this file.

*The clock is injected, never frozen globally.* ADR-0018's counter suffix fires
only when two same-mode puzzles are created inside one clock minute, and its
own Consequences call that "easy to under-test". Every timestamped assertion
here therefore runs against a :class:`NameContext` holding a fixed clock, so
the collision branch is exercised on demand rather than when a test happens to
straddle a minute boundary.

*The name is checked on the aggregate, not on a helper's return value*, wherever
the pipeline can produce one: AC-042/043/044 say "when the puzzle is created",
so the assertions are about ``generate(...).name``. The naming layer is called
directly only for the ``image`` mode, which has no grid source yet (CARD-015).

*The file the name produces is checked too.* The puzzle's name is the only
source of the export filename stem (``orchestrator._filename_stem``), which is
what keeps the name a user reads and the file they get from drifting apart;
the last section is the evidence for that, sanitization included.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from nonogram import cli, export, orchestrator
from nonogram.errors import InvalidPuzzleName
from nonogram.orchestrator import (
    GenerationRequest,
    NameContext,
    Puzzle,
    export_puzzle,
    generate,
)

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_orchestrator.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"

#: AC-042's own instant: 2026-08-27, 14:30.
NOON = datetime(2026, 8, 27, 14, 30)

#: The name that instant produces in random mode (AC-042).
NOON_RANDOM_NAME = "random-2026-08-27-1430"

#: The smallest supported grid (FR-001), so the naming tests run the real
#: pipeline rather than a mocked one without paying for a big solve.
FAST_SIZE = 10

#: A pinned seed whose first random 10x10 candidate at 50% is uniquely solvable
#: (swept over seeds 0..11), so no naming test spends a retry it did not ask
#: for. Re-pin by re-running that sweep if it stops behaving this way.
FAST_SEED = 0


def _grid(*patterns: str) -> list[list[bool]]:
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: Two solutions — the opposite diagonal has the same all-``(1,)`` clues — so
#: the uniqueness check rejects it and POL-001 asks for another candidate.
AMBIGUOUS = _grid("█·", "·█")

#: Exactly one solution: row 0's ``(2,)`` forces the top, column 0's ``(2,)``
#: then forces row 1.
UNIQUE = _grid("██", "█·")


def _request(**overrides: object) -> GenerationRequest:
    """A minimal random-mode request; overrides name the field under test."""
    fields: dict[str, object] = {
        "mode": "random",
        "width": FAST_SIZE,
        "height": FAST_SIZE,
        "density": 50,
        "seed": FAST_SEED,
    }
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


def _at(*moments: datetime) -> NameContext:
    """A naming context whose clock reads ``moments`` in order.

    The last moment repeats, so a context built from one instant is simply a
    frozen clock — the common case — while a two-instant one is a run that
    crossed a minute boundary.
    """
    readings = iter(moments)
    last = moments[-1]

    def clock() -> datetime:
        nonlocal last
        last = next(readings, last)
        return last

    return NameContext(clock=clock)


class _ScriptedSource:
    """One sourcing mode, replaced by a fixed sequence of grids (see
    tests/test_orchestrator.py, where the same device drives the retry tests)."""

    def __init__(self, *grids: list[list[bool]]) -> None:
        self._grids = list(grids)
        self.calls = 0

    def __call__(self, *arguments: object) -> list[list[bool]]:
        self.calls += 1
        return self._grids[min(self.calls - 1, len(self._grids) - 1)]


def _install_source(
    monkeypatch: pytest.MonkeyPatch, source: _ScriptedSource
) -> _ScriptedSource:
    monkeypatch.setattr(orchestrator.sourcing, "for_mode", lambda mode: source)
    return source


def _exported(puzzle: Puzzle) -> Path:
    """The single path a one-format export of ``puzzle`` wrote."""
    (path,) = export_puzzle(puzzle)
    return path


# ==========================================================================
# AC-042 — TestPuzzleName_AutoGeneratesModeTimestampForRandomMode
# ==========================================================================


def test_puzzle_name_auto_generates_mode_timestamp_for_random_mode() -> None:
    """A random-mode run with no --name, at 14:30 on 2026-08-27."""
    puzzle = generate(_request(), names=_at(NOON))

    assert puzzle.name == NOON_RANDOM_NAME


def test_puzzle_name_auto_generates_mode_timestamp_for_random_mode_with_a_counter() -> (
    None
):
    """ADR-0018's collision branch, on a clock that cannot leave the minute.

    Minute precision means two random-mode puzzles created inside one minute
    would otherwise carry the identical default name; the ADR resolves that at
    the point the name is chosen rather than leaving it to export-time
    suffixing, with the same "-1", "-2" mechanism ADR-0017 uses one layer
    later.
    """
    names = _at(NOON)

    first = generate(_request(), names=names)
    second = generate(_request(), names=names)
    third = generate(_request(), names=names)

    assert first.name == NOON_RANDOM_NAME
    assert second.name == f"{NOON_RANDOM_NAME}-1"
    assert third.name == f"{NOON_RANDOM_NAME}-2"


def test_puzzle_name_auto_generates_mode_timestamp_for_random_mode_per_minute() -> None:
    """The counter is a same-minute device, not a run counter: the next minute
    starts from the plain name again."""
    names = _at(NOON, datetime(2026, 8, 27, 14, 31))

    first = generate(_request(), names=names)
    second = generate(_request(), names=names)

    assert first.name == NOON_RANDOM_NAME
    assert second.name == "random-2026-08-27-1431"


def test_the_auto_name_names_the_mode_it_was_generated_in() -> None:
    """FR-015 gives image mode the same shape as random mode. CARD-015 has not
    landed a grid source for it, so this is the naming layer alone."""
    assert _at(NOON).name_for(GenerationRequest(mode="image")) == (
        "image-2026-08-27-1430"
    )


def test_the_auto_name_and_the_export_stem_are_one_convention() -> None:
    """FR-015's name format is not re-spelled next to CARD-007's: the naming
    layer calls ``export.default_stem``, so the two cannot drift apart."""
    assert _at(NOON).name_for(_request()) == export.default_stem(
        "random", moment=NOON
    )


# ==========================================================================
# AC-043 — TestPuzzleName_AutoGeneratesFromLibraryKey
# ==========================================================================


def test_puzzle_name_auto_generates_from_library_key() -> None:
    """A library-mode run with no --name is named after the key, verbatim —
    no mode prefix and no timestamp."""
    puzzle = generate(
        GenerationRequest(mode="library", library_key="cat", width=15, height=15, seed=3),
        names=_at(NOON),
    )

    assert puzzle.name == "cat"


def test_puzzle_name_auto_generates_from_library_key_without_a_counter() -> None:
    """ADR-0018's counter is about same-*minute* timestamps; a key is not one.

    Two "cat" puzzles are two renderings of the same picture, and ADR-0016
    states outright that an auto-generated key "is not guaranteed unique",
    leaving that collision to ADR-0017's export-time suffix. Suffixing here
    would also break AC-043 for the second run of the day.
    """
    names = _at(NOON)
    request = GenerationRequest(
        mode="library", library_key="cat", width=15, height=15, seed=3
    )

    assert names.name_for(request) == "cat"
    assert names.name_for(request) == "cat"


def test_a_library_run_without_a_key_is_still_named_before_it_fails() -> None:
    """Naming runs first, so it must not be the thing that reports a missing
    key: the request falls back to the timestamp name and then fails in
    sourcing with the error it deserves (AC-006)."""
    request = GenerationRequest(mode="library", width=15, height=15, seed=3)

    assert _at(NOON).name_for(request) == "library-2026-08-27-1430"


# ==========================================================================
# AC-044 — TestPuzzleName_OverrideViaFlag
# ==========================================================================


def test_puzzle_name_override_via_flag() -> None:
    """--name replaces the auto-generated default, character for character."""
    puzzle = generate(_request(name="my-cat-puzzle"), names=_at(NOON))

    assert puzzle.name == "my-cat-puzzle"


def test_puzzle_name_override_via_flag_beats_the_library_key() -> None:
    puzzle = generate(
        GenerationRequest(
            mode="library", library_key="cat", width=15, height=15, seed=3, name="my-cat-puzzle"
        ),
        names=_at(NOON),
    )

    assert puzzle.name == "my-cat-puzzle"


def test_an_overridden_name_is_never_counter_suffixed() -> None:
    """The counter disambiguates *generated* names. A user who names two runs
    the same meant it; their files are separated by ADR-0017 at export."""
    names = _at(NOON)

    first = generate(_request(name="mine"), names=names)
    second = generate(_request(name="mine"), names=names)

    assert (first.name, second.name) == ("mine", "mine")


def test_puzzle_name_override_via_flag_is_carried_through_by_the_cli() -> None:
    """COMP-001's whole part in FR-015: parse the flag, hand it inward."""
    args = cli.build_parser().parse_args(["generate", "--name", "my-cat-puzzle"])

    assert args.name == "my-cat-puzzle"


def test_the_name_flag_is_optional() -> None:
    """No --name is ``None`` — "auto-generate one" — and not an empty name."""
    assert cli.build_parser().parse_args(["generate"]).name is None


def test_the_cli_reaches_the_orchestrator_with_the_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[GenerationRequest] = []

    def spy(request: GenerationRequest) -> Puzzle:
        requests.append(request)
        return generate(request, names=_at(NOON))

    monkeypatch.setattr(orchestrator, "generate", spy)

    argv = ["generate", "--name", "my-cat-puzzle", "--size", "10", "--density", "50"]

    assert cli.main([*argv, "--seed", str(FAST_SEED)]) == 0
    assert [request.name for request in requests] == ["my-cat-puzzle"]


# ==========================================================================
# AC-045 (negative) — TestPuzzleName_RejectsEmptyName
# ==========================================================================


def test_puzzle_name_rejects_empty_name() -> None:
    """--name "" is not a name; the run is refused."""
    with pytest.raises(InvalidPuzzleName):
        generate(_request(name=""), names=_at(NOON))


def test_puzzle_name_rejects_empty_name_before_a_puzzle_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """"...and no puzzle is created": the name is resolved before the seed is
    drawn and before the first candidate is sourced."""
    source = _install_source(monkeypatch, _ScriptedSource(UNIQUE))

    with pytest.raises(InvalidPuzzleName):
        generate(_request(name=""), names=_at(NOON))

    assert source.calls == 0


def test_puzzle_name_rejects_empty_name_when_it_is_only_whitespace() -> None:
    """A blank name is empty for every consumer it has — a PDF header that
    renders as nothing (FR-016), a filename stem that sanitizes away."""
    with pytest.raises(InvalidPuzzleName):
        generate(_request(name="   "), names=_at(NOON))


def test_puzzle_name_rejects_empty_name_inward_of_argparse() -> None:
    """ADR-0010, guardrail G-5: the parser accepts the empty string — it is
    syntactically a value — and the domain is what refuses it."""
    args = cli.build_parser().parse_args(["generate", "--name", ""])

    assert args.name == ""


def test_puzzle_name_rejects_empty_name_with_an_invalid_input_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The user-visible half of AC-045, and that nothing was written."""
    exit_code = cli.main(
        [
            "generate",
            "--name",
            "",
            "--size",
            "10",
            "--density",
            "50",
            "--seed",
            "3",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.INVALID_INPUT
    assert "name" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


# ==========================================================================
# Guardrail G-6 — one name per run, set at creation, stable across retries
# ==========================================================================


def test_the_name_is_resolved_once_and_survives_every_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AGG-001: a retry replaces the candidate, not the puzzle.

    The clock moves a minute on every reading, so a name regenerated inside
    the loop would change (and pick up a counter suffix); the assertion that
    it did not is therefore about the aggregate's lifecycle, not about the
    clock being slow.
    """
    source = _install_source(monkeypatch, _ScriptedSource(AMBIGUOUS, AMBIGUOUS, UNIQUE))
    names = _at(NOON, datetime(2026, 8, 27, 14, 31), datetime(2026, 8, 27, 14, 32))

    puzzle = generate(_request(), names=names)

    assert source.calls == 3
    assert puzzle.regenerate.attempts == 3
    assert puzzle.name == NOON_RANDOM_NAME
    assert names.issued == {NOON_RANDOM_NAME}


def test_the_name_is_the_same_object_the_run_started_with(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The aggregate is not re-created per retry, so neither is its name."""
    _install_source(monkeypatch, _ScriptedSource(AMBIGUOUS, UNIQUE))
    seen: list[str | None] = []

    original = Puzzle.record_candidate

    def spy(self: Puzzle, grid: list[list[bool]]) -> object:
        seen.append(self.name)
        return original(self, grid)

    monkeypatch.setattr(Puzzle, "record_candidate", spy)

    puzzle = generate(_request(name="mine"), names=_at(NOON))

    assert seen == ["mine", "mine"]
    assert puzzle.name == "mine"


# ==========================================================================
# The name *is* the export filename stem (FR-015 -> ADR-0016/ADR-0017)
# ==========================================================================


def _ready(out: Path, **overrides: object) -> Puzzle:
    """A confirmed-unique puzzle bound for ``out``, straight from the pipeline."""
    fields: dict[str, object] = {"export_formats": (export.JSON,), "out": out}
    fields.update(overrides)
    return generate(_request(**fields), names=_at(NOON))


def test_the_export_filename_is_the_puzzles_name(tmp_path: Path) -> None:
    """One run, one name: what the puzzle is called is what the file is called,
    rather than a timestamp computed a second time at export."""
    puzzle = _ready(tmp_path)

    assert _exported(puzzle).name == f"{NOON_RANDOM_NAME}.json"


def test_a_library_export_is_named_after_the_key(tmp_path: Path) -> None:
    """The case where the two conventions would visibly disagree: the puzzle is
    "cat", so the file is ``cat.json`` and not ``library-<timestamp>.json``."""
    puzzle = generate(
        GenerationRequest(
            mode="library",
            library_key="cat",
            width=15, height=15,
            seed=3,
            export_formats=(export.JSON,),
            out=tmp_path,
        ),
        names=_at(NOON),
    )

    assert _exported(puzzle).name == "cat.json"


def test_an_overridden_name_names_the_file_too(tmp_path: Path) -> None:
    puzzle = _ready(tmp_path, name="my-cat-puzzle")

    assert _exported(puzzle).name == "my-cat-puzzle.json"


def test_a_name_cannot_write_outside_the_output_directory(tmp_path: Path) -> None:
    """ADR-0016's "sanitized for filesystem-safe characters", as the property
    that matters: --name is user input on its way into a path."""
    destination = tmp_path / "out"
    puzzle = _ready(destination, name="../../escaped")

    path = _exported(puzzle)

    assert path.parent == destination
    assert path.name == "escaped.json"
    assert path.stem == "escaped"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize(
    ("name", "stem"),
    [
        ("a b/c", "a-b-c"),
        ("cat:2026", "cat-2026"),
        ("cat*", "cat"),
        # Non-ASCII letters are filesystem-safe and must survive sanitization
        # intact rather than being truncated to whatever ASCII remains
        # (regression coverage for the Unicode-aware \w allow-list).
        ("кот-2026", "кот-2026"),
        ("café", "café"),
        ("日本語", "日本語"),
    ],
)
def test_a_name_keeps_its_shape_on_the_aggregate_however_the_file_is_spelled(
    tmp_path: Path, name: str, stem: str
) -> None:
    """Sanitization is applied to the filename, never to the name: AC-044 asks
    for the name back verbatim, and the PDF header (CARD-014) shows it as
    typed."""
    puzzle = _ready(tmp_path, name=name)

    path = _exported(puzzle)

    assert puzzle.name == name
    assert path.parent == tmp_path
    assert path.suffix == ".json"
    assert path.stem == stem


def test_a_name_that_sanitizes_to_nothing_falls_back_to_the_convention(
    tmp_path: Path,
) -> None:
    """"..." is a legal display name and an illegal filename; the file gets the
    auto-generated stem rather than a dotfile or a path segment."""
    puzzle = _ready(tmp_path, name="...")

    path = _exported(puzzle)

    assert puzzle.name == "..."
    assert path.parent == tmp_path
    assert path.name.startswith("random-") and path.name.endswith(".json")
    assert path.stem.startswith("random-")


def test_an_unnamed_aggregate_still_exports_under_the_card_007_convention(
    tmp_path: Path,
) -> None:
    """A ``Puzzle`` assembled by hand rather than by ``generate`` carries no
    name; CARD-007's stand-in stem covers it, which is the same convention."""
    puzzle = Puzzle(
        request=_request(export_formats=(export.JSON,), out=tmp_path), seed=1
    )
    puzzle.record_candidate(UNIQUE)
    puzzle.confirm_uniqueness(1)

    assert puzzle.name is None
    assert _exported(puzzle).name.startswith("random-")


def test_every_format_of_one_run_shares_the_name(tmp_path: Path) -> None:
    """The stem is resolved once per run, so a multi-format export is one named
    puzzle in several formats (CARD-007's property, now keyed on the name)."""
    puzzle = _ready(
        tmp_path,
        name="my-cat-puzzle",
        export_formats=(export.JSON, export.PNG, export.SVG),
    )

    paths = export_puzzle(puzzle)

    assert {path.stem for path in paths} == {"my-cat-puzzle"}
    assert sorted(path.suffix for path in paths) == [".json", ".png", ".svg"]


def test_the_cli_reports_the_named_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end, as a user sees it: COMP-001 -> COMP-002 -> COMP-007."""
    exit_code = cli.main(
        [
            "generate",
            "--name",
            "my-cat-puzzle",
            "--size",
            "10",
            "--density",
            "50",
            "--seed",
            "3",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    assert "my-cat-puzzle.json" in capsys.readouterr().out
    assert [path.name for path in tmp_path.iterdir()] == ["my-cat-puzzle.json"]


def test_the_naming_context_is_not_shared_between_processes_by_accident() -> None:
    """The default context is per-process state (ADR-0018's "current run" for a
    single-puzzle CLI). It is an object rather than a module-level global so a
    caller — a test, a future batch mode — can scope its own."""
    assert isinstance(orchestrator.DEFAULT_NAMES, NameContext)
    drift = orchestrator.DEFAULT_NAMES.clock() - datetime.now()
    assert abs(drift.total_seconds()) < 5


def test_the_unseeded_default_still_names_a_puzzle() -> None:
    """The real clock path, exercised once: no injected context at all."""
    puzzle = generate(_request())

    assert puzzle.name is not None
    assert puzzle.name.startswith("random-")
