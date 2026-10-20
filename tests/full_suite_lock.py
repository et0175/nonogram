"""CARD-255 — refuse to start a run while another worktree holds the lock.

Every full-suite gate writes ``meta/kanban/.full-suite.lock`` naming its
holder, its worktree, its commit and when it started — and until this module
existed, **nothing read it**. The gate's own guard refuses to *start* beside
another pytest, which is a check at the door that cannot stop someone entering
afterwards. CARD-225's build gate 2 ran fifteen minutes alongside a 288-test
Chromium suite in another worktree and reported two failures that were not the
tree: a UUID sentinel handed a float, a loopback server nothing answered on.
Both are green in the next gate. One gate re-run, one attribution written down
and then withdrawn.

So the lock becomes a control: a pytest run stops before collection while
*another* worktree holds it.

Identity is the worktree, not a pid
-----------------------------------
The guard must refuse a foreign lock and ignore its own, and "its own" cannot
be a pid: the gate script writes the lock and then launches pytest as a
**child**, so no pid the file could carry is ever the pid of the process this
code runs in. What every gate does do is run pytest in the worktree it names
in the file. So the holder's identity is ``worktree:``, compared with the tree
this module was imported from — and a lock that names no worktree is refused
rather than assumed to be ours (ADR-0039/R2: a shape the guard cannot analyse
is a refusal, never a silent pass).

The stale rule is an age threshold, not a pid
---------------------------------------------
A holder that dies leaves the file behind, and a board that cannot run tests
at all is worse than a contended one. The rule chosen is **age**, for one
reason: the gate scripts write ``at:`` and do not write a pid, and G-4 forbids
changing them to make this guard work. A pid rule would therefore never fire
on a single real lock — a claim with no reach (ADR-0039/R1). ``at:`` is in
every real lock today, and the file's mtime stands in when it is missing or
unreadable.

The threshold (:data:`STALE_SECONDS`) clears the longest hold this board has
on record by more than four times; see its own comment. Anything shorter than
the threshold is for the override, which is immediate and loud.

Why its own module. The same reason as ``tests/hang_guard.py`` and
``tests/database_guard.py``: ``tests/conftest.py`` imports its hook, and the
decision stays a pure function that can be put every case in front of without
starting a process. The card's Touches named only the conftest; this follows
the two guards already there instead, and the conftest is still where the hook
is registered.
"""

from __future__ import annotations

import calendar
import os
import time
from pathlib import Path

__all__ = [
    "LOCK_PATH_VAR",
    "OVERRIDE",
    "STALE_SECONDS",
    "current_verdict",
    "default_lock_path",
    "lock_age_seconds",
    "lock_path",
    "main_repo_root",
    "parse_fields",
    "read_lock",
    "report_line",
    "this_worktree",
    "verdict",
]

#: Set this to run while another worktree holds the lock. Named in every
#: refusal, so the way out is never a thing to go and look up, and announced
#: on every run that uses it — the one thing worse than a contended gate is a
#: board that cannot run tests at all, and the one thing worse than that is a
#: suppression nobody can see in the output.
#:
#: No gate script sets it, which is what makes it an override
#: (``test_the_gate_scripts_do_not_set_the_override``).
OVERRIDE = "NONOGRAM_IGNORE_FULL_SUITE_LOCK"

#: Points the guard at a different lock file. Exists for this guard's own
#: tests: they must never create or delete the board's real lock, because a
#: gate may be holding it. Unset — which is every real run, gate or agent —
#: the path is :func:`default_lock_path`, the one file every gate writes.
LOCK_PATH_VAR = "NONOGRAM_FULL_SUITE_LOCK"

#: How old a lock may be before it is treated as abandoned.
#:
#: Six hours. The number is bounded from below by the longest lock-hold this
#: board has recorded: CARD-245's gate wrapper held it 4126s (its pytest
#: session was 1196s of that; the gap is recorded there as unexplained). A
#: threshold near that figure would hand a *running* gate's window to a second
#: pytest, which is the defect this module removes, so it sits above it with
#: room — and the cost of being generous is bounded by the override, which
#: needs no wait at all.
STALE_SECONDS = 21600.0

#: Where the lock lives, relative to the main repo root.
LOCK_RELATIVE_PATH = ("meta", "kanban", ".full-suite.lock")

#: Printed in this order when a lock is reported, each as the gate wrote it.
#: Some gates fold the reason into ``holder`` and some write ``why`` as its own
#: field; both shapes are in use, so both are printed.
REPORTED_FIELDS = ("holder", "why", "worktree", "commit", "at")


def this_worktree() -> Path:
    """The tree this run belongs to: ``tests/`` sits directly under it.

    The module's own location, not the working directory — a selection run
    from somewhere else is still a run of *this* tree's suite, and that is
    what the holder comparison is about.
    """
    return Path(__file__).resolve().parent.parent


def main_repo_root(worktree: Path) -> Path:
    """The main checkout behind ``worktree``, which may be itself.

    Every gate script writes the **main** repo's lock whichever worktree it
    runs the suite in, so a linked worktree has to follow its ``.git`` file
    back there; a per-worktree path would be a guard that cannot see the only
    contention there is. A linked worktree's ``.git`` is a file reading
    ``gitdir: <main>/.git/worktrees/<name>``.
    """
    dot_git = worktree / ".git"
    try:
        pointer = dot_git.read_text(encoding="utf-8") if dot_git.is_file() else ""
    except OSError:
        pointer = ""
    if pointer.startswith("gitdir:"):
        gitdir = Path(pointer.split(":", 1)[1].strip())
        for parent in gitdir.parents:
            if parent.name == ".git":
                return parent.parent
    return worktree


def default_lock_path(worktree: Path | None = None) -> Path:
    """The real file the gates write — the production default, always."""
    root = main_repo_root(worktree if worktree is not None else this_worktree())
    return root.joinpath(*LOCK_RELATIVE_PATH)


def lock_path() -> Path:
    """The lock this process reads: :data:`LOCK_PATH_VAR`, else the real one."""
    named = os.getenv(LOCK_PATH_VAR)
    if named:
        return Path(named)
    return default_lock_path()


def read_lock(path: Path) -> str | None:
    """The lock's text, or ``None`` when there is no lock.

    An existing file that cannot be read comes back as ``""`` rather than
    ``None``: it names no worktree, so it is refused. "There is a lock here
    and I cannot read it" is not the same answer as "there is no lock".
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    except OSError:
        return ""


def parse_fields(text: str) -> dict[str, str]:
    """``key: value`` lines, in the order written, first occurrence winning.

    Lines that are not ``key: value`` are ignored, which is how the old
    free-text lock (``echo "profiling run, started ..."``) parses to nothing
    and is therefore refused rather than mistaken for this run's own.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        key = key.strip().lower()
        if not separator or not key or " " in key:
            continue
        fields.setdefault(key, value.strip())
    return fields


def _same_tree(one: str, other: str) -> bool:
    """Do two paths name the same checkout?

    Through ``realpath`` both sides: ``/tmp`` is a symlink on macOS and a
    worktree reached through one is the same worktree.
    """
    return os.path.realpath(os.path.expanduser(one.strip())) == os.path.realpath(
        os.path.expanduser(other.strip())
    )


def _epoch(stamp: str) -> float | None:
    """A gate's ``at:`` value as epoch seconds, or ``None`` if unreadable.

    ``calendar.timegm`` is ``time.gmtime``'s inverse, which is the whole
    reason it is here: the stamps are UTC (``...Z``) and ``time.mktime`` would
    read them as local time and be hours out twice a year.
    """
    try:
        return float(calendar.timegm(time.strptime(stamp.strip(), "%Y-%m-%dT%H:%M:%SZ")))
    except (ValueError, TypeError):
        return None


def lock_age_seconds(
    fields: dict[str, str], *, path: Path | None = None, now: float | None = None
) -> float | None:
    """How long ago the lock was taken, or ``None`` when nothing says.

    ``at:`` first, because that is the moment the gate took the lock and is
    what every gate script writes. The file's mtime stands in when ``at`` is
    missing or malformed, so the stale rule still applies to the free-text
    locks ``tests/README.md`` used to describe. An unknown age is never
    treated as old (:func:`verdict` keeps the refusal).
    """
    when = _epoch(fields.get("at", ""))
    if when is None and path is not None:
        try:
            when = path.stat().st_mtime
        except OSError:
            when = None
    if when is None:
        return None
    return (time.time() if now is None else now) - when


def _describe(fields: dict[str, str], age_seconds: float | None, path: Path | None) -> str:
    """The holder, field by field, as a block to paste into a message."""
    lines = []
    for key in REPORTED_FIELDS:
        lines.append(f"  {key + ':':10}{fields.get(key, '(not in the lock file)')}")
    for key in sorted(set(fields) - set(REPORTED_FIELDS)):
        lines.append(f"  {key + ':':10}{fields[key]}")
    age = "unknown" if age_seconds is None else f"{age_seconds:.0f}s"
    lines.append(f"  {'age:':10}{age} (stale after {STALE_SECONDS:.0f}s)")
    lines.append(f"  {'lock:':10}{path if path is not None else '(unnamed)'}")
    return "\n".join(lines)


def _one_line(fields: dict[str, str]) -> str:
    """Who holds it, in a form that fits on a terminal line."""
    holder = fields.get("holder") or fields.get("why") or "a holder the lock does not name"
    where = fields.get("worktree", "an unnamed worktree")
    return f"{holder} ({where})"


def verdict(
    lock_text: str | None,
    *,
    worktree: str,
    age_seconds: float | None,
    overridden: bool,
    path: Path | None = None,
) -> tuple[bool, str | None]:
    """May this run start? And what must it say?

    Returns ``(allowed, said)``. ``said`` is ``None`` when there is nothing to
    report — no lock, or our own gate's lock — and a message whenever a
    decision was taken that somebody has to be able to see afterwards: the
    refusal, a stale lock walked past, the override used.
    """
    if lock_text is None:
        return True, None

    fields = parse_fields(lock_text)
    held_by = fields.get("worktree")
    if held_by and _same_tree(held_by, worktree):
        # The gate writes the lock and then runs the suite in the worktree it
        # named. Refusing here would stop every gate on the board; this is the
        # case "treat every lock as foreign" reds.
        return True, None

    if overridden:
        return True, (
            f"full-suite lock: held by {_one_line(fields)} — "
            f"running anyway because {OVERRIDE} is set"
        )

    if age_seconds is not None and age_seconds >= STALE_SECONDS:
        return True, (
            f"full-suite lock: ignoring a stale lock — {_one_line(fields)} took it "
            f"{age_seconds:.0f}s ago, past the {STALE_SECONDS:.0f}s threshold, and is "
            f"presumed gone. Delete {path} if it is."
        )

    unnamed = (
        ""
        if held_by
        else (
            "\nThis lock names no worktree, so it cannot be recognised as this run's own "
            "and is refused rather than assumed harmless.\n"
        )
    )
    return False, (
        f"Refusing to start: another worktree holds the full-suite lock.\n"
        f"\n"
        f"{_describe(fields, age_seconds, path)}\n"
        f"{unnamed}"
        f"\n"
        f"A full-suite gate is running there, and a second pytest on this host is what "
        f"made CARD-225's gate report two failures that were not the tree. Wait for the "
        f"file to disappear — it is deleted when that run ends.\n"
        f"\n"
        f"If the holder is gone and the file is not:\n"
        f"    {OVERRIDE}=1 pytest ...\n"
        f"\n"
        f"A lock older than {STALE_SECONDS:.0f}s is ignored without asking."
    )


def current_verdict() -> tuple[bool, str | None]:
    """:func:`verdict` for the lock and environment this process is in."""
    path = lock_path()
    text = read_lock(path)
    if text is None:
        return True, None
    fields = parse_fields(text)
    return verdict(
        text,
        worktree=str(this_worktree()),
        age_seconds=lock_age_seconds(fields, path=path),
        overridden=bool(os.getenv(OVERRIDE)),
        path=path,
    )


#: What this session decided, for the hooks that report it. ``None`` on nearly
#: every run, which is why both report hooks are silent by default.
_ANNOUNCEMENT: str | None = None


def report_line() -> str | None:
    """The run-header line, or ``None`` when there is nothing to say."""
    return _ANNOUNCEMENT


def pytest_configure(config) -> None:
    """Stop the run before collection while another worktree holds the lock.

    First in ``tests/conftest.py``'s ``pytest_configure``, before the database
    guard and before any fixture exists, let alone one that connects (G-1).
    """
    import pytest

    global _ANNOUNCEMENT

    allowed, said = current_verdict()
    _ANNOUNCEMENT = said if allowed else None
    if not allowed:
        raise pytest.UsageError(said)


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Say it again at the end, where ``-q`` cannot hide it.

    ``pyproject`` sets ``addopts = "-q"``, and at that verbosity pytest prints
    no run header at all — so an override or an ignored stale lock announced
    only through :func:`report_line` would be invisible in every gate and
    every agent's selection, which are the only runs there are.
    """
    if _ANNOUNCEMENT:
        terminalreporter.write_line(_ANNOUNCEMENT, yellow=True)
