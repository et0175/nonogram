"""CARD-109 — the suite refuses a database it was not pointed at on purpose.

    AC-1  a DATABASE_URL that is not a test database stops the run
    AC-2  unset behaves exactly as before
    AC-3  db_required still runs when reachable, still skips when not
    AC-4  the four files that picked it up silently no longer reach a database
    AC-5  the guard's own behaviour is watched, not asserted

`create_app()` reads `DATABASE_URL` and goes wherever it points. On
2026-09-21 that cost a stray row in the development database, and then four
e2e failures when that database was emptied mid-session — the suite's result
became a property of the shell rather than of the code.

The guard refuses rather than silently unsetting the variable. A developer who
pointed the suite somewhere by accident is told; one who did it on purpose is
told how to say so. Quietly absorbing it would be the same mistake as the
``except (ImportError, Exception): pass`` CARD-104 deleted — the whole problem
here is that nothing warned.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.database_guard import OPT_OUT, verdict

REPO = Path(__file__).parent.parent


# --------------------------------------------------------------------------
# AC-1 / AC-2 — the rule
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@localhost:5432/nonogram_poc",
        "postgresql://u:p@db.example.com:5432/nonogram",
        "postgresql://u:p@localhost:5432/mealplanner",
        "postgresql://u:p@dpg-abc123.oregon-postgres.render.com/nonogram_prod",
    ],
)
def test_a_database_that_is_not_a_test_database_is_refused(url):
    allowed, reason = verdict(url, opted_out=False)

    assert allowed is False
    assert "nonogram_poc" in reason or url.rsplit("/", 1)[-1] in reason, (
        "the refusal does not name the database it refused"
    )


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@localhost:5432/nonogram_test",
        "postgresql://u:p@localhost:5432/test_nonogram",
        "postgresql://u:p@localhost:5432/nonogram_poc_test",
        "sqlite:///./nonogram_test.db",
    ],
)
def test_a_test_database_is_allowed(url):
    allowed, _reason = verdict(url, opted_out=False)

    assert allowed is True


def test_no_database_at_all_is_the_ordinary_case():
    """AC-2: unset is how the suite normally runs, and must stay silent."""
    allowed, reason = verdict(None, opted_out=False)

    assert allowed is True
    assert "not set" in reason.lower()


def test_the_opt_out_allows_a_foreign_database_and_says_so():
    """Someone who means it can say so; the run still reports what it reached."""
    url = "postgresql://u:p@localhost:5432/nonogram_poc"

    allowed, reason = verdict(url, opted_out=True)

    assert allowed is True
    assert OPT_OUT in reason, "the header does not say the guard was opted out of"


def test_the_refusal_never_repeats_the_password():
    """A URL carries a credential; a refusal is printed and often pasted."""
    allowed, reason = verdict(
        "postgresql://dbo9er:hunter2@db.example.com:5432/nonogram", opted_out=False
    )

    assert allowed is False
    # The password, the username, and the credential pair as written. Checked
    # as distinctive strings rather than plausible words: an earlier version
    # of this test used "admin" as the username and failed on the refusal's
    # own prose ("builds admin apps"), which proves nothing about leaking.
    assert "hunter2" not in reason
    assert "dbo9er" not in reason
    assert "@db.example.com" not in reason


# --------------------------------------------------------------------------
# AC-5 — the guard is watched doing it, in a real run
# --------------------------------------------------------------------------


def _run_pytest(env_extra, *args):
    import os

    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), **env_extra}
    env.pop("DATABASE_URL", None)
    env.update({k: v for k, v in env_extra.items()})
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_a_hostile_database_url_aborts_a_real_run():
    """AC-5. Not 'the function returns False' — the run actually stops."""
    result = _run_pytest(
        {"DATABASE_URL": "postgresql://u:p@localhost:5432/nonogram_poc"},
        "tests/test_card_109_database_guard.py::test_no_database_at_all_is_the_ordinary_case",
    )

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "nonogram_poc" in combined
    assert OPT_OUT in combined, "the refusal does not say how to proceed deliberately"


def test_the_same_run_succeeds_with_the_opt_out():
    result = _run_pytest(
        {
            "DATABASE_URL": "postgresql://u:p@localhost:5432/nonogram_poc",
            OPT_OUT: "1",
        },
        "tests/test_card_109_database_guard.py::test_no_database_at_all_is_the_ordinary_case",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_header_says_what_the_guard_decided():
    result = _run_pytest(
        {"DATABASE_URL": "postgresql://u:p@localhost:5432/nonogram_test"},
        "tests/test_card_109_database_guard.py::test_no_database_at_all_is_the_ordinary_case",
        "-v",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "nonogram_test" in result.stdout


# --------------------------------------------------------------------------
# AC-4 — the four files no longer reach a database
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "tests/e2e/test_admin_workflow.py",
        "tests/test_admin_image_uniqueness.py",
        "tests/test_admin_regrade.py",
        "tests/test_card_050_quality_recognizability.py",
    ],
)
def test_no_app_building_file_leaves_the_database_to_chance(path):
    """Every file that builds an app decides what database it gets.

    Deciding means either clearing the variable or setting it — both are a
    choice, and `test_admin_regrade.py` legitimately makes the second one,
    pointing at a SQLite file of its own.

    The first version of this test looked for ``delenv("DATABASE_URL"`` alone
    and reported all four as exposed. Two of them were clearing it with
    ``os.environ.pop`` and the third was setting its own; **one** was genuinely
    exposed. Measuring one spelling and calling it coverage is the same mistake
    this suite has made about class names twice today, so the check now names
    both ways of deciding.
    """
    source = (REPO / path).read_text()

    decides = (
        'delenv("DATABASE_URL"' in source
        or 'setenv("DATABASE_URL"' in source
        or 'environ.pop("DATABASE_URL"' in source
    )
    assert decides, (
        f"{path} builds an app without deciding what DATABASE_URL should be, "
        "so it reaches whatever the developer's shell happens to name"
    )


def test_the_fixtures_restore_what_they_change():
    """`os.environ.pop` clears it for the rest of the session, not the test.

    That made whether a later test saw a database depend on whether an earlier
    one had run — order-dependence hiding inside a fix. `monkeypatch` restores.
    """
    for path in (
        "tests/e2e/test_admin_workflow.py",
        "tests/test_admin_image_uniqueness.py",
        "tests/test_card_050_quality_recognizability.py",
    ):
        source = (REPO / path).read_text()
        assert 'environ.pop("DATABASE_URL"' not in source, (
            f"{path} clears DATABASE_URL without restoring it"
        )
