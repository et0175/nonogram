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
this module was imported from — and a lock that does not name a worktree this
guard can resolve to a tree is refused rather than assumed to be ours
(ADR-0039/R2: a shape the guard cannot analyse is a refusal, never a silent
pass).

Two values are that shape and both take the same branch: a **missing**
``worktree:``, and a **relative** one. ``realpath`` resolves a relative value
against the *reading* process's cwd, and every gate runs pytest from its own
worktree root — so a foreign holder's ``worktree: .`` would resolve, inside
every other worktree, to that worktree, be recognised as this run's own, and
let the run through saying nothing at all. It names a path, but not a tree.
No gate script writes one (all three write ``worktree: $WT`` absolutely), but
``tests/README.md`` tells a human to hand-write a lock, and that is reach
enough.

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

CARD-370 and CARD-377 — a full suite takes the lock itself
----------------------------------------------------------
Until these cards the lock was mandatory on refusal and advisory on
acquisition: nothing in the tree wrote it, so a full suite that did not take
it by hand ran unseen, and the next one to take it refused every child pytest
the first was still starting (wave 76: 37 failures that were not the tree).

**Which run is a full suite** is decided from what the run *collected*, never
from how it was spelled: every test module on disk under ``tests/`` produced a
collection report, nothing was deselected, and no argument named a single
node. ``pytest``, ``pytest tests``, ``pytest .`` and ``pytest tests/*.py`` are
all the same full suite by that rule, and ``-k``, ``-m``, ``--deselect``,
``--ignore``, ``--lf`` or a path list that leaves one module out are all
narrower. See :func:`is_full_suite`.

**A full suite with no lock in its way takes it** before the first test runs
(``O_EXCL``, so two that race cannot both win), says so in the terminal
summary, and removes it when the session ends. It writes ``pid``, ``host``
and a ``token``, exports the token to its children through
:data:`OWNER_VAR` so the pytests it starts recognise the lock as theirs, and
touches the file every :data:`HEARTBEAT_SECONDS` from a daemon thread.

**A lock left by a dead run** no longer waits six hours. On the host that
wrote it, a ``pid`` no process answers to is gone at once; from another host,
whose pids mean nothing here, a heartbeat older than
:data:`HEARTBEAT_STALE_SECONDS` is. :data:`STALE_SECONDS` is unchanged and
still governs the gate scripts' locks, which carry neither field.

**A second run in the same worktree** is still let through, because a gate
writes the lock and then runs pytest there — but when the lock carries a token
that is not this process's, it says so instead of saying nothing.
"""

from __future__ import annotations

import calendar
import fnmatch
import os
import secrets
import socket
import threading
import time
from pathlib import Path

__all__ = [
    "HEARTBEAT_SECONDS",
    "HEARTBEAT_STALE_SECONDS",
    "LOCK_PATH_VAR",
    "OVERRIDE",
    "OWNER_VAR",
    "STALE_SECONDS",
    "acquire",
    "heartbeat_age_seconds",
    "holder_alive",
    "is_full_suite",
    "lock_text_for",
    "release",
    "test_modules_on_disk",
    "current_verdict",
    "default_lock_path",
    "lock_age_seconds",
    "lock_path",
    "main_repo_root",
    "parse_fields",
    "read_lock",
    "redirect_note",
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
#: Any non-empty value turns it on, ``=0`` and ``=false`` included. That is
#: the same spelling ``tests/database_guard.py`` reads its own opt-out with,
#: kept deliberately so the two guards have one convention rather than two —
#: and an overridden run announces itself in the terminal summary, so the
#: surprising spelling cannot become a quiet suppression. Said out loud here
#: *and* held by a test, because a documented value semantics with no control
#: is a sentence a tidy-up can falsify in silence:
#: ``test_any_non_empty_value_turns_the_override_on_including_zero``.
#:
#: No gate script sets it, which is what makes it an override
#: (``test_the_gate_scripts_do_not_set_the_override``).
OVERRIDE = "NONOGRAM_IGNORE_FULL_SUITE_LOCK"

#: Points the guard at a different lock file. Exists for this guard's own
#: tests: they must never create or delete the board's real lock, because a
#: gate may be holding it. Unset, the path is :func:`default_lock_path`, the
#: one file every gate writes.
#:
#: That it *is* unset on a real run is held rather than asserted, and only as
#: far as it is measured: no **tracked** file in this tree names it, by
#: ``test_nothing_in_the_tree_sets_either_of_the_guards_env_switches``, the
#: same whole-tree scan that holds the override. Untracked files are outside
#: ``git grep``'s reach and the gate scripts live outside this repo entirely;
#: those are read, not held. What closes the rest is that a run which does set
#: it says so — :func:`redirect_note`, for the same reason the override
#: announces itself.
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

#: Set by this module, and only by it, in the process that took the lock, so
#: that the pytests that process starts inherit it and recognise the lock as
#: their own run's. Not a switch: setting it by hand to a lock's token makes a
#: run read that lock as its parent's, and nothing else.
OWNER_VAR = "NONOGRAM_FULL_SUITE_LOCK_OWNER"

#: How often a lock this module took is touched.
HEARTBEAT_SECONDS = 60.0

#: How long a heartbeat may be silent before its holder is presumed gone. Read
#: only when the holder's pid cannot be checked (another host): fifteen beats,
#: so a loaded machine that starves the thread for a few minutes is not read
#: as a dead one. On the writing host the pid answers sooner and exactly.
HEARTBEAT_STALE_SECONDS = 900.0

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

    **Exact** equality of the two resolved paths, never a prefix test: on
    this board the worktrees are siblings whose paths share a prefix
    (``…-card-25`` and ``…-card-255``; the main checkout is a prefix of all of
    them), so a prefix rule would read the shorter holder's lock as the longer
    tree's own and pass a foreign lock in silence.

    Through ``realpath`` on both sides: ``/tmp`` is a symlink on macOS and a
    worktree reached through one is the same worktree; a trailing slash and a
    leading ``~`` normalise to the same answer too.

    Both values must already be absolute — ``realpath`` resolves a relative
    one against *this* process's cwd, which would make ``.`` mean "wherever
    the reader is". :func:`verdict` establishes that with :func:`_names_a_tree`
    before it asks.
    """
    return os.path.realpath(os.path.expanduser(one.strip())) == os.path.realpath(
        os.path.expanduser(other.strip())
    )


def _names_a_tree(value: str | None) -> bool:
    """Can this ``worktree:`` value be resolved to a tree at all?

    A missing value cannot, and neither can a relative one, for the reason in
    :func:`_same_tree`. Both are the shape ADR-0039/R2 calls unanalysable, and
    :func:`verdict` refuses both through one branch rather than inventing a
    second vocabulary for the second one.
    """
    return bool(value) and os.path.isabs(os.path.expanduser(value.strip()))


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


def holder_alive(fields: dict[str, str], *, host: str | None = None) -> bool | None:
    """Is the process that wrote this lock still running? ``None``: cannot tell.

    Only a lock that names both ``pid`` and ``host`` can be asked, and only on
    that host — a pid from another machine names nothing here. The gate
    scripts write neither, so their locks always answer ``None`` and keep the
    age rule.
    """
    here = socket.gethostname() if host is None else host
    if fields.get("host") != here:
        return None
    try:
        pid = int(fields.get("pid", ""))
    except ValueError:
        return None
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def heartbeat_age_seconds(
    fields: dict[str, str], *, path: Path | None, now: float | None = None
) -> float | None:
    """Seconds since a heartbeating lock was last touched; ``None`` otherwise.

    Only a lock that says it heartbeats (a ``heartbeat`` field, which this
    module writes) is read this way. Any other lock's mtime is its acquisition
    time and says nothing about whether its holder is alive.
    """
    if "heartbeat" not in fields or path is None:
        return None
    try:
        touched = path.stat().st_mtime
    except OSError:
        return None
    return (time.time() if now is None else now) - touched


def _describe(fields: dict[str, str], age_seconds: float | None, path: Path | None) -> str:
    """The holder, field by field, as a block to paste into a message."""
    lines = []
    for key in REPORTED_FIELDS:
        lines.append(f"  {key + ':':10}{fields.get(key, '(not in the lock file)')}")
    for key in sorted(set(fields) - set(REPORTED_FIELDS)):
        lines.append(f"  {key + ':':10}{fields[key]}")
    if age_seconds is None:
        age = "unknown"
    elif age_seconds < 0:
        # Clock skew between the writer and this reader, or a hand-written
        # stamp. The verdict is unaffected — a negative age is below the
        # threshold, so the refusal stands — but "-3600s" reads as nonsense to
        # the person being refused, so it is printed as what it is.
        age = f"stamped {-age_seconds:.0f}s in the future (clock skew?)"
    else:
        age = f"{age_seconds:.0f}s"
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
    alive: bool | None = None,
    heartbeat_age: float | None = None,
    own_token: str | None = None,
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
    names_a_tree = _names_a_tree(held_by)
    gone = _gone(alive, heartbeat_age)
    if names_a_tree and _same_tree(held_by or "", worktree):
        # The gate writes the lock and then runs the suite in the worktree it
        # named. Refusing here would stop every gate on the board; this is the
        # case "treat every lock as foreign" reds.
        token = fields.get("token")
        if not token or token == own_token:
            return True, None
        # CARD-377: a lock this module wrote, in this worktree, for a run this
        # process does not descend from. Still allowed — refusing would stop
        # a gate — but no longer silent, so one worktree shared by two runs
        # has something in the output that says so.
        if gone:
            return True, (
                f"full-suite lock: ignoring a lock in this worktree left by "
                f"{_one_line(fields)}, which {gone}. Delete {path} if it is still there."
            )
        return True, (
            f"full-suite lock: another run in this worktree holds the lock — "
            f"{_one_line(fields)}, taken at {fields.get('at', '(no at: field)')}. "
            f"This run is not that one; two runs in one worktree share its database "
            f"and its files."
        )

    if overridden:
        return True, (
            f"full-suite lock: held by {_one_line(fields)} — "
            f"running anyway because {OVERRIDE} is set"
        )

    if gone:
        return True, (
            f"full-suite lock: ignoring a stale lock — {_one_line(fields)} "
            f"{gone}. Delete {path} if it is still there."
        )

    if age_seconds is not None and age_seconds >= STALE_SECONDS:
        return True, (
            f"full-suite lock: ignoring a stale lock — {_one_line(fields)} took it "
            f"{age_seconds:.0f}s ago, past the {STALE_SECONDS:.0f}s threshold, and is "
            f"presumed gone. Delete {path} if it is."
        )

    if names_a_tree:
        unnamed = ""
    else:
        why = (
            f"its worktree: value {held_by!r} is not an absolute path, so it would "
            "resolve to whichever tree happened to read it"
            if held_by
            else "it has no worktree: line at all"
        )
        unnamed = (
            f"\nThis lock does not name a worktree this guard can resolve to a tree "
            f"({why}), so it cannot be recognised as this run's own and is refused "
            f"rather than assumed harmless.\n"
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


def _gone(alive: bool | None, heartbeat_age: float | None) -> str | None:
    """Why the holder is presumed gone, in words, or ``None`` if it may be alive.

    A pid answered on its own host outranks the heartbeat: a test that holds
    the interpreter long enough to starve the heartbeat thread is still a live
    run, and only the pid can say so.
    """
    if alive is False:
        return "is no longer running (its pid answers to no process on this host)"
    if alive is None and heartbeat_age is not None and heartbeat_age >= HEARTBEAT_STALE_SECONDS:
        return (
            f"stopped its heartbeat {heartbeat_age:.0f}s ago, past the "
            f"{HEARTBEAT_STALE_SECONDS:.0f}s threshold"
        )
    return None


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
        alive=holder_alive(fields),
        heartbeat_age=heartbeat_age_seconds(fields, path=path),
        own_token=os.getenv(OWNER_VAR) or None,
    )


#: What this session decided, for the hooks that report it. ``None`` on nearly
#: every run, which is why both report hooks are silent by default.
_ANNOUNCEMENT: str | None = None


def report_line() -> str | None:
    """The run-header line, or ``None`` when there is nothing to say."""
    return _ANNOUNCEMENT


def redirect_note() -> str | None:
    """What a run whose lock path was redirected has to say, or ``None``.

    :data:`LOCK_PATH_VAR` decides which file the verdict is taken from, and
    until CARD-256 it decided it in silence. Pointed at a path holding no
    lock, the guard answered ``386 passed``, ``current_verdict() ==
    (True, None)`` and ``report_line() is None`` — so on a board where the
    real file would have refused the run, that is a run allowed that should
    have been refused, printing nothing at all.

    The redirection stays — these tests may never create or delete the board's
    own lock — so what is added is the sentence, for the reason the override
    has one: a switch that changes this guard's verdict without saying so is
    indistinguishable from the guard not working.

    ``None`` whenever the variable is unset or empty — every run nothing has
    redirected, which :data:`LOCK_PATH_VAR` says how far is held. ``if named``
    is the same reading :func:`lock_path` gives the value, so the note cannot
    claim a redirection that did not happen.
    """
    named = os.getenv(LOCK_PATH_VAR)
    if not named:
        return None
    return (
        f"full-suite lock: reading the lock from {named}, not the board's own "
        f"{default_lock_path()} — {LOCK_PATH_VAR} is set"
    )


def test_modules_on_disk(tests_dir: Path, patterns: list[str] | tuple[str, ...]) -> set[Path]:
    """Every file under ``tests_dir`` that pytest would collect as a test module.

    ``patterns`` is the run's own ``python_files``, so the rule follows the
    configuration rather than restating it. Hidden directories and
    ``__pycache__`` are left out, as pytest's default ``norecursedirs`` does.
    """
    found: set[Path] = set()
    for folder, dirs, files in os.walk(tests_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for name in files:
            if name.endswith(".py") and any(fnmatch.fnmatch(name, pat) for pat in patterns):
                found.add(Path(folder, name).resolve())
    return found


def is_full_suite(
    *,
    on_disk: set[Path],
    collected: set[Path],
    deselected: int,
    args: list[str] | tuple[str, ...],
) -> bool:
    """Did this run collect the whole suite? (CARD-370 AC-1.)

    Derived from the collection, so no spelling of the command line changes the
    answer: a run is full when every test module on disk was collected,
    nothing was deselected afterwards, and no argument named a single node
    (``file::test`` collects its whole module but runs one test). An empty
    ``on_disk`` — a tree this rule cannot see — answers *full*: the doubtful
    case takes the lock, which costs another worktree a wait, rather than
    running unlocked, which cost wave 76 thirty-seven failures.
    """
    if any("::" in str(arg) for arg in args):
        return False
    if deselected:
        return False
    return on_disk <= collected


def lock_text_for(*, worktree: str, token: str, pid: int, host: str, now: float) -> str:
    """The lock a full suite writes: the gate scripts' fields, plus its own."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    return (
        f"holder: pytest full suite (pid {pid})\n"
        f"worktree: {worktree}\n"
        f"at: {stamp}\n"
        f"host: {host}\n"
        f"pid: {pid}\n"
        f"token: {token}\n"
        f"heartbeat: file mtime, every {HEARTBEAT_SECONDS:.0f}s\n"
    )


#: The lock this process took, while it holds it: path, token, stop event.
_HELD: dict | None = None

#: This process's :class:`_Session`, once :func:`pytest_configure` registered it.
_SESSION = None


def acquire(path: Path, *, worktree: str) -> tuple[bool, str]:
    """Take the lock at ``path`` if nobody holds it. ``(taken, what to say)``.

    ``O_CREAT | O_EXCL``: of two full suites that both found no lock, exactly
    one creates the file and the other is told who did. A stale lock (the
    verdict already walked past it) is removed first and then taken the same
    way. On success the token goes into :data:`OWNER_VAR` for this process's
    children and a daemon thread starts touching the file.
    """
    global _HELD
    token = secrets.token_hex(8)
    text = lock_text_for(
        worktree=worktree, token=token, pid=os.getpid(), host=socket.gethostname(), now=time.time()
    )
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False, "another run took it first"
    except OSError as error:
        return False, f"it could not be written ({error.strerror})"
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    stop = threading.Event()

    def beat() -> None:
        while not stop.wait(HEARTBEAT_SECONDS):
            try:
                os.utime(path)
            except OSError:
                return

    threading.Thread(target=beat, name="full-suite-lock-heartbeat", daemon=True).start()
    os.environ[OWNER_VAR] = token
    _HELD = {"path": path, "token": token, "stop": stop}
    return True, f"full-suite lock: this run is a full suite and holds the lock ({path})"


def release() -> None:
    """Remove the lock this process took — only if it is still ours."""
    global _HELD
    held, _HELD = _HELD, None
    if held is None:
        return
    held["stop"].set()
    if os.environ.get(OWNER_VAR) == held["token"]:
        del os.environ[OWNER_VAR]
    text = read_lock(held["path"])
    if text is not None and parse_fields(text).get("token") == held["token"]:
        try:
            held["path"].unlink()
        except OSError:
            pass


def _add_announcement(line: str) -> None:
    global _ANNOUNCEMENT
    _ANNOUNCEMENT = f"{_ANNOUNCEMENT}\n{line}" if _ANNOUNCEMENT else line


class _Session:
    """The hooks that need the collection: registered by :func:`pytest_configure`."""

    def __init__(self, config) -> None:
        self.config = config
        self.collected: set[Path] = set()
        self.deselected = 0
        self.failed_under_foreign_lock = 0

    def pytest_collectreport(self, report) -> None:
        nodeid = report.nodeid
        if nodeid.endswith(".py") and "::" not in nodeid:
            self.collected.add((self.config.rootpath / nodeid).resolve())

    def pytest_deselected(self, items) -> None:
        self.deselected += len(items)

    def pytest_collection_finish(self, session) -> None:
        tests_dir = this_worktree() / "tests"
        full = is_full_suite(
            on_disk=test_modules_on_disk(tests_dir, self.config.getini("python_files")),
            collected=self.collected,
            deselected=self.deselected,
            args=self.config.args,
        )
        if not full or self.config.option.collectonly:
            return
        path = lock_path()
        text = read_lock(path)
        if text is not None:
            allowed, said = current_verdict()
            if not allowed:
                # Taken between configure and now, by another worktree.
                import pytest

                raise pytest.UsageError(said or "full-suite lock taken during collection")
            fields = parse_fields(text)
            gone = _gone(holder_alive(fields), heartbeat_age_seconds(fields, path=path))
            stale = gone or (lock_age_seconds(fields, path=path) or 0.0) >= STALE_SECONDS
            if not stale:
                return  # a gate in this worktree, or the override: theirs to hold
            try:
                path.unlink()
            except OSError:
                pass
        taken, said = acquire(path, worktree=str(this_worktree()))
        if taken:
            _add_announcement(said)
            return
        allowed, refusal = current_verdict()
        if not allowed:
            import pytest

            raise pytest.UsageError(refusal or "full-suite lock taken during collection")
        _add_announcement(
            f"full-suite lock: this run is a full suite and does NOT hold the lock — {said}"
        )

    def pytest_runtest_logreport(self, report) -> None:
        """CARD-370 AC-3: a failure while another worktree holds the lock says so there."""
        if not report.failed:
            return
        allowed, said = current_verdict()
        if allowed:
            return
        self.failed_under_foreign_lock += 1
        report.sections.append(
            (
                "full-suite lock",
                "Another worktree held the full-suite lock when this test failed, so "
                "any pytest it started was refused before collecting anything. "
                "Re-run it alone before reading this as the tree's failure.\n\n" + (said or ""),
            )
        )

    def pytest_unconfigure(self, config) -> None:
        release()


def pytest_configure(config) -> None:
    """Stop the run before collection while another worktree holds the lock.

    First in ``tests/conftest.py``'s ``pytest_configure``, before the database
    guard and before any fixture exists, let alone one that connects (G-1).
    """
    import pytest

    global _ANNOUNCEMENT

    allowed, said = current_verdict()
    lines = [line for line in (redirect_note(), said) if line] if allowed else []
    _ANNOUNCEMENT = "\n".join(lines) or None
    if not allowed:
        raise pytest.UsageError(said)
    if not config.pluginmanager.has_plugin("full_suite_lock_session"):
        session = _Session(config)
        config.pluginmanager.register(session, "full_suite_lock_session")
        global _SESSION
        _SESSION = session


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Say it again at the end, where ``-q`` cannot hide it.

    ``pyproject`` sets ``addopts = "-q"``, and at that verbosity pytest prints
    no run header at all — so an override or an ignored stale lock announced
    only through :func:`report_line` would be invisible in every gate and
    every agent's selection, which are the only runs there are.
    """
    if _ANNOUNCEMENT:
        terminalreporter.write_line(_ANNOUNCEMENT, yellow=True)
    session = _SESSION
    if session is not None and session.failed_under_foreign_lock:
        terminalreporter.write_line(
            f"full-suite lock: {session.failed_under_foreign_lock} failure(s) happened while "
            f"another worktree held the lock; each carries a 'full-suite lock' section.",
            yellow=True,
        )
