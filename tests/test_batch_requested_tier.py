"""CARD-181 — a batch remembers the tier it asked for, and its pages show it.

CARD-138 let a random batch ask for a tier and passed it to the generator as an
argument, storing it nowhere. This card stores the canonical value
(``parse_tier(...).value``) on the memory-mode ``BatchJob`` and on the DB-mode
``batches`` row (new nullable column, migration 014), reads it back in both DB
readers, and shows it on ``/batches``, ``/batches/<id>`` and ``/batch/<id>``.

These tests are about *recording*, not generation: ``_generate_random_batch``
is replaced by a stub that records the arguments it was called with, so a test
can also see that the tier still reaches it as an argument (G-1). Generation to
a tier is tested in ``tests/test_batch_difficulty_target.py``.

DB mode runs over ``tests/helpers/db.py:sqlite_session_scope`` so it never
skips; the Postgres path of migration 014 is recorded on the card (AC-6).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

from nonogram.admin.batch_generator import (
    MIN_RANDOM_BATCH_COUNT,
    BatchGenerator,
    BatchJob,
    BatchStatus,
)
from tests.helpers.db import sqlite_session_scope

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# fixtures and helpers
# --------------------------------------------------------------------------


class _GenerationCalls:
    """Stands in for ``BatchGenerator._generate_random_batch``; records calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, batch_id, difficulty_tier=None):
        self.calls.append((batch_id, difficulty_tier))


@pytest.fixture
def generation(monkeypatch):
    calls = _GenerationCalls()
    monkeypatch.setattr(
        BatchGenerator,
        "_generate_random_batch",
        lambda self, batch_id, difficulty_tier=None: calls(batch_id, difficulty_tier),
    )
    return calls


def _random_batch(generator: BatchGenerator, tier: str | None) -> str:
    return generator.create_batch(
        count=MIN_RANDOM_BATCH_COUNT,
        sizes=[10],
        theme="test",
        source="random",
        difficulty_tier=tier,
    )


def _image_batch(generator: BatchGenerator, tier: str | None) -> str:
    return generator.create_batch(
        count=1,
        sizes=[15],
        theme="image",
        source="images",
        difficulty_tier=tier,
    )


def _stored_tiers(scope) -> dict[str, str | None]:
    """``{batch id: requested_tier}`` read with plain SQL in a fresh session.

    Plain SQL rather than the ORM, so the check is of what is on disk and not
    of whatever the mapped class would hand back.
    """
    from sqlalchemy import text

    with scope() as db:
        rows = db.execute(text("SELECT id, requested_tier FROM batches")).all()
    # SQLAlchemy's UUID type stores 32 hex digits on SQLite.
    return {str(uuid.UUID(str(row_id))): tier for row_id, tier in rows}


def _job_in_list(generator: BatchGenerator, batch_id: str) -> BatchJob:
    [job] = [job for job in generator.list_batches() if job.batch_id == batch_id]
    return job


# --------------------------------------------------------------------------
# AC-1 — memory mode
# --------------------------------------------------------------------------


class TestBatchRequestedTier_MemoryModeRecordsTheTier:
    def test_the_canonical_tier_is_on_the_job_and_in_the_list(self, generation):
        generator = BatchGenerator(session_factory=None)

        batch_id = _random_batch(generator, "MEDIUM")

        assert generator.get_batch_status(batch_id).requested_tier == "medium"
        assert _job_in_list(generator, batch_id).requested_tier == "medium"

    def test_the_tier_still_reaches_generation_as_an_argument(self, generation):
        """G-1: storing the tier does not change how generation receives it."""
        generator = BatchGenerator(session_factory=None)

        batch_id = _random_batch(generator, "MEDIUM")

        assert generation.calls == [(batch_id, "medium")]


# --------------------------------------------------------------------------
# AC-2 — DB mode
# --------------------------------------------------------------------------


class TestBatchRequestedTier_DbModeStoresAndReadsBackTheTier:
    def test_the_row_holds_the_canonical_tier_and_both_readers_return_it(
        self, tmp_path, generation
    ):
        scope = sqlite_session_scope(tmp_path)
        generator = BatchGenerator(session_factory=scope)

        batch_id = _random_batch(generator, "Hard")

        assert _stored_tiers(scope) == {batch_id: "hard"}
        assert generator.get_batch_status(batch_id).requested_tier == "hard"
        assert _job_in_list(generator, batch_id).requested_tier == "hard"
        assert generator.get_batch_status(batch_id).status is BatchStatus.COMPLETE

    def test_the_tier_still_reaches_generation_as_an_argument(
        self, tmp_path, generation
    ):
        scope = sqlite_session_scope(tmp_path)
        generator = BatchGenerator(session_factory=scope)

        batch_id = _random_batch(generator, "Hard")

        assert generation.calls == [(batch_id, "hard")]


# --------------------------------------------------------------------------
# AC-3 — untargeted and image batches store NULL
# --------------------------------------------------------------------------


_UNRECORDED = [
    pytest.param(_random_batch, None, id="random-untargeted"),
    pytest.param(_image_batch, None, id="images-untargeted"),
    pytest.param(_image_batch, "medium", id="images-with-a-tier"),
]


class TestBatchRequestedTier_UntargetedAndImageBatchesStoreNull:
    @pytest.mark.parametrize("make, tier", _UNRECORDED)
    def test_memory_mode(self, generation, make, tier):
        generator = BatchGenerator(session_factory=None)

        batch_id = make(generator, tier)

        assert generator.get_batch_status(batch_id).requested_tier is None
        assert _job_in_list(generator, batch_id).requested_tier is None

    @pytest.mark.parametrize("make, tier", _UNRECORDED)
    def test_db_mode(self, tmp_path, generation, make, tier):
        scope = sqlite_session_scope(tmp_path)
        generator = BatchGenerator(session_factory=scope)

        batch_id = make(generator, tier)

        assert _stored_tiers(scope) == {batch_id: None}
        assert generator.get_batch_status(batch_id).requested_tier is None
        assert _job_in_list(generator, batch_id).requested_tier is None


# --------------------------------------------------------------------------
# AC-4 — migration 014 is reversible
# --------------------------------------------------------------------------


_OLD_ROW_ID = "11111111111111111111111111111111"


class TestBatchRequestedTier_Migration014IsReversible:
    """Executed, not described: a pre-014 SQLite database, then 014 is run.

    The database is built in today's shape, ``requested_tier`` is dropped back
    off, a batch row is inserted and the database is stamped at 013 — the
    pattern of ``TestBookInk_Migration013BackfillsEveryExistingBook``.
    """

    @pytest.fixture
    def pre_014_db(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine, text

        from nonogram.db.models import Base

        url = f"sqlite:///{tmp_path / 'pre014.db'}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE batches DROP COLUMN requested_tier"))
            connection.execute(
                text(
                    "INSERT INTO batches (id, status, source, total_count, "
                    "completed_count, puzzle_count, sizes, theme, "
                    "quality_filter, error_message, created_at, updated_at) "
                    "VALUES (:id, 'complete', 'random', 12, 11, 11, '[10, 15]', "
                    "'winter', 40, 'Only 11 of 12 came out medium.', "
                    "'2026-09-01 10:00:00', '2026-09-01 10:05:00')"
                ),
                {"id": _OLD_ROW_ID},
            )
        engine.dispose()

        # migrations/env.py reads DATABASE_URL before the config's URL.
        monkeypatch.setenv("DATABASE_URL", url)
        from alembic import command

        command.stamp(self._config(url), "013")
        return url

    @staticmethod
    def _config(url: str):
        from alembic.config import Config

        config = Config()
        config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
        config.set_main_option("sqlalchemy.url", url)
        return config

    @staticmethod
    def _batches(url: str):
        """``(columns by name, the rows as dicts)`` of the ``batches`` table."""
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(url)
        try:
            columns = {c["name"]: c for c in inspect(engine).get_columns("batches")}
            with engine.connect() as connection:
                rows = [
                    dict(row._mapping)
                    for row in connection.execute(text("SELECT * FROM batches"))
                ]
            return columns, rows
        finally:
            engine.dispose()

    def test_the_fixture_really_is_a_pre_014_database(self, pre_014_db):
        columns, rows = self._batches(pre_014_db)
        assert "requested_tier" not in columns
        assert len(rows) == 1

    def test_up_down_up(self, pre_014_db):
        from alembic import command

        config = self._config(pre_014_db)
        _, [before] = self._batches(pre_014_db)

        command.upgrade(config, "014")
        columns, [upgraded] = self._batches(pre_014_db)
        assert "requested_tier" in columns
        assert columns["requested_tier"]["nullable"] is True
        assert upgraded["requested_tier"] is None, "no backfill: the old row reads NULL"
        assert {k: v for k, v in upgraded.items() if k != "requested_tier"} == before

        command.downgrade(config, "013")
        columns, [downgraded] = self._batches(pre_014_db)
        assert "requested_tier" not in columns
        assert downgraded == before, "the old row and its other columns are unchanged"

        command.upgrade(config, "014")
        columns, [again] = self._batches(pre_014_db)
        assert "requested_tier" in columns
        assert again["requested_tier"] is None

    def test_014_revises_013_and_is_the_only_head(self):
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(self._config("sqlite://"))
        revision = script.get_revision("014")
        assert revision.down_revision == "013"
        assert script.get_heads() == ["014"]


# --------------------------------------------------------------------------
# AC-5 — the pages
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADMIN_ALLOWED_HOST", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def _row_for(html: str, batch_id: str) -> str:
    """The ``/batches`` table row that names this batch."""
    [row] = [
        row
        for row in re.findall(r"<tr>.*?</tr>", html, flags=re.S)
        if batch_id[:8] in row
    ]
    return row


def _cells(row: str) -> list[str]:
    return [
        re.sub(r"<[^>]+>", "", cell).strip()
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
    ]


def _header_cells(html: str) -> list[str]:
    [head] = re.findall(r"<thead>.*?</thead>", html, flags=re.S)
    return [cell.strip() for cell in re.findall(r"<th[^>]*>(.*?)</th>", head, flags=re.S)]


def _tier_asked_dd(html: str) -> str:
    [value] = re.findall(r"<dt>Tier asked</dt>\s*<dd[^>]*>(.*?)</dd>", html, flags=re.S)
    return value.strip()


def _lede(html: str) -> str:
    [lede] = re.findall(r'<p class="lede">(.*?)</p>', html, flags=re.S)
    return lede.strip()


class TestBatchRequestedTier_PagesShowWhatTheBatchAskedFor:
    @pytest.fixture
    def pages(self, admin_app, generation):
        targeted = _random_batch(admin_app.batch_generator, "medium")
        untargeted = _random_batch(admin_app.batch_generator, None)
        client = admin_app.test_client()

        def get(path):
            response = client.get(path)
            assert response.status_code == 200, path
            return response.get_data(as_text=True)

        return targeted, untargeted, get

    def test_the_list_has_a_tier_asked_column_after_source(self, pages):
        targeted, untargeted, get = pages
        html = get("/batches")

        headers = _header_cells(html)
        assert headers[headers.index("Source") + 1] == "Tier asked"
        column = headers.index("Tier asked")
        assert _cells(_row_for(html, targeted))[column] == "Medium"
        assert _cells(_row_for(html, untargeted))[column] == "—"
        assert "Any" not in _row_for(html, untargeted)

    def test_the_batch_puzzles_lede_says_what_was_asked_for(self, pages):
        targeted, untargeted, get = pages

        assert _lede(get(f"/batches/{targeted}")).endswith(", asked for Medium.")
        null_lede = _lede(get(f"/batches/{untargeted}"))
        assert "asked for" not in null_lede
        assert "Any" not in null_lede
        assert null_lede.endswith("sizes 10.")

    def test_the_batch_status_page_has_a_tier_asked_row(self, pages):
        targeted, untargeted, get = pages

        assert _tier_asked_dd(get(f"/batch/{targeted}")) == "Medium"
        assert _tier_asked_dd(get(f"/batch/{untargeted}")) == "—"

    def test_the_tier_is_plain_text_not_the_graded_tier_badge(self, pages):
        """A request is not a grade: the ``_tier.html`` badge never carries it.

        Checked on the raw markup of the list cell and the status-page value,
        so a badge (``<span class="badge tier" ...>Medium</span>``) fails here
        even though its text would still read "Medium".
        """
        targeted, _, get = pages
        html = get("/batches")
        column = _header_cells(html).index("Tier asked")
        raw_cells = re.findall(r"<td[^>]*>(.*?)</td>", _row_for(html, targeted), flags=re.S)

        assert raw_cells[column].strip() == "Medium"
        assert _tier_asked_dd(get(f"/batch/{targeted}")) == "Medium"


class TestBatchRequestedTier_LabelFilter:
    """The filter the three templates use: COMP-006's label, or None."""

    @pytest.mark.parametrize(
        "stored, label",
        [
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
            ("Medium", "Medium"),
            (None, None),
            ("", None),
            ("extreme", None),
            ("any", None),
        ],
    )
    def test_stored_value_to_label(self, stored, label):
        from nonogram.admin.app import requested_tier_label

        assert requested_tier_label(stored) == label

    def test_it_is_registered_for_the_templates(self, admin_app):
        assert admin_app.jinja_env.filters["requested_tier_label"]("hard") == "Hard"
