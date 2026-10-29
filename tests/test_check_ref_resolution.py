"""CARD-308 — the architecture validator's verifying refs, resolved twice.

**This module is a DETECTOR, not a repair.** The honest fix is to resolve a
model ref against a **definition** instead of against text, and that code lives
in ``forge_1``'s ``validators/utils.py``, outside this repository. Nothing here
changes what the validator reports. What it does is make the validator's one
systematic blind spot *visible inside the suite*, so that a warning count
falling for the wrong reason stops being invisible.

The mechanism, measured
=======================

``validators/utils.symbol_exists()`` is::

    git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'

a **text** search. Its own docstring claims ``-w`` resolves a name "to its
``def test_x`` definition"; that is false — ``-w`` only enforces word
boundaries. So a ref is "alive" as soon as its string appears anywhere in
tracked, non-Markdown content, *including* content that merely talks about it.

``meta/architecture/**`` and every ``*.md`` are excluded, so the registry
genuinely cannot self-validate and ``board.md`` resolves nothing. Everything
else tracked is in domain. The in-domain writers that are **mandatory pipeline
bookkeeping** — nobody's mistake, and none of them removable — are:

* ``meta/review/**`` — the CARD SYNC PROTOCOL copies each cycle's review report
  into the main repo one-way, because ``/commit`` excludes ``meta/`` from card
  branches and ``forge:fix`` / ``forge:commit`` / ``forge:retrospective`` read
  those reports. Measured twice: a ref's warning disappeared on the sync commit
  alone, with the test still absent.
* ``meta/kanban/dispatcher.state`` — no ``.md`` extension, so unlike
  ``board.md`` it is **inside** the search's domain. The orchestrator wrote a
  ref name into it while recording this very defect, and thereby became one of
  that ref's two load-bearing resolvers.
* ``meta/kanban/backlog-scored.yml``, ``meta/kanban/waves.yml`` — scoring and
  wave bookkeeping, same property.
* ``meta/profiling/*.txt`` — duration logs, which name every node id that ran.

**Author discipline cannot be the remedy.** CARD-291's cycle-1 reviewer knew
the hazard, split one ref token across two YAML pieces so its report would not
revive it, and verified the split worked — and still retired a live warning,
because a review report's most-quoted refs are its own card's, and on ``main``
those were the dead ones. Any guard that depends on a report being written
carefully is not a guard.

**Why a pathspec narrowing is not the fix.** ``:(exclude)meta/review`` looks
like the cheap repair and is insufficient: the same erosion arrives from
``meta/profiling/**``, from ``meta/kanban/dispatcher.state`` and
``backlog-scored.yml``, and — the limit case — from **prose inside ``tests/``
itself**. ADR-0006/R1's ref has zero definitions anywhere and is resolved by
over a hundred files, two of which are a comment and a docstring in
``tests/test_export_pdf.py`` and ``tests/test_puzzle_editor_ui.py``.
``tests/`` cannot be excluded: it is the only place the search *must* look. So
no pathspec can separate "a file that defines the test" from "a file that
mentions it", and only a definition-based resolver can. That argument is the
point of this module's existence; it is recorded in ADR-0039's section
"The validator's own ref resolver is a control that cannot fail".

What is resolved here, and how
==============================

Two resolvers over the same derived ref set:

* :func:`_loose_resolution` — an independent reimplementation of
  ``git grep -lw`` in Python, over ``git ls-files`` minus the validator's two
  pathspec excludes. Built as a trie regex so one pass answers every ref.
  :func:`test_the_loose_resolver_agrees_with_git_grep_itself` proves it against
  the real ``git grep -lw`` on a derived sample, because an instrument that
  silently answers nothing is indistinguishable from a clean board.
* :func:`_strict_resolution` — the same question asked of **definitions only**:
  a ``def`` or ``class`` line.

A ref where the two disagree is reported, in **both** directions (EC):

``loose alive / strict dead``
    the validator says checked, nothing defines it.
``loose dead / strict alive``
    the validator says dead, a definition exists — ``-w`` treats ``_`` as a
    word character, so ``git grep -w PropertyTest_Foo`` does **not** match
    ``def test_PropertyTest_Foo``, and a node id's whole ``path::name`` string
    is never a code identifier at all.

Neither direction is folded into the other and neither is dropped.

The three ref forms, and the one the board cannot resolve
========================================================

``nodeid`` — ``tests/foo.py::test_bar``
    an **address**. Strictly resolvable: the named file must define the named
    symbol. 20 of this board's 23 resolve that way.
``path`` — ``meta/ops/image_abandonment_…py``
    a script that stands in for a test. Strictly resolvable: the file is
    tracked.
``bare`` — ``TestFoo_DoesBar``
    a **label**, not a symbol. On this board the convention never required the
    model's bare ref to be the test's Python name: ADR-0022/R4's
    ``PropertyTest_BareSize_Derives…SourceShape`` is implemented
    by ``def test_a_bare_size_derives_the_shorter_side_from_the_source_shape``.
    163 bare refs therefore have no containing definition, and flagging all of
    them would be a census of a naming convention rather than a detector of
    erosion.

So the **gate** (:func:`test_no_verifying_ref_is_resolved_only_by_pipeline_bookkeeping`)
is drawn where the evidence is unambiguous for every form: a ref that the loose
search resolves, that no definition resolves, and that **nothing in the code
tree mentions at all** — the only things keeping it alive are the bookkeeping
writers listed above. The wider disagreement set is not dropped; it is pinned
whole by :func:`test_the_two_directions_of_disagreement_are_exactly_the_measured_ones`,
so a ref moving between any two classes reds the suite and has to be read.

What a report here does NOT claim
=================================

"This ref does not resolve to a definition" is **not** "this behaviour is
untested". A ref may be a superseded name for a test that still exists under a
different one — measured: the model carries
``TestBookPdf_TwoUpUpperSlot…FixedTopEdge`` while ``tests/`` defines
``class TestBookPdf_TwoUpUpperSlotDoesNotShare…TopRow``, which is
a *different claim*, not a rename of the same one. Both the flag and the
distinction are correct: what is broken is the model's pointer, and deciding
whether the behaviour is covered is the repair's job (CARD-307), not the
detector's. Reading a report here as a coverage gap overstates it in one
direction; reading a green run as "the refs are honest" overstates it in the
other, and only the second is dangerous.

G-2: this file does not revive what it detects
==============================================

A guard that lists dead refs *spells them in tracked, non-Markdown code* and so
revives them through the mechanism it exists to catch — the defect, re-created
by its own detector. Two defences, both load-bearing:

1. Every set here is **derived at run time** from ``requirements.yml``,
   ``trace.yml`` and the ADR set. No ref list is written down. The baselines
   that are written down are a count and a SHA-256 of the sorted class, which
   revive nothing.
2. The two refs AC-4 pins must be named to be pinned, so they are named in
   pieces that are joined at run time, never as a whole token. Every *other*
   ref this module's prose quotes as an example is truncated with an ellipsis
   for the same reason: ``…`` is not a word character, so ``git grep -w``
   cannot complete the token.
   :func:`test_this_module_resolves_no_verifying_ref_at_all` asserts the
   property over **every** ref in the model, not just those two — which is the
   half CARD-291's reviewer did not have, and the reason its careful split
   still made no difference. Measured: on this module's first run that test
   named three refs its own docstring had revived -- which is how ready a
   file written *about* the defect is to commit it.

No skips, by construction
=========================

Nothing here is conditional: no ``skipif``, no conditional ``xfail``, no
``pytest.skip``, and no early ``return`` out of a test body. A missing registry
file, an unreadable tree or a ``git`` that fails is a **failure**, never a pass
— per ADR-0039/R2, and because a skipped gate is an ungated door.
``tests/test_suite_profile.py``'s ``_conditional_silences`` AST-walks this file
along with every other guarded source; it reports ``[]`` for it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ARCH = REPO_ROOT / "meta" / "architecture"
REQUIREMENTS = ARCH / "requirements.yml"
TRACE = ARCH / "trace.yml"
ADR_DIR = ARCH / "decisions" / "adr"

#: The validator's own pathspec excludes, copied from
#: ``validators/utils.code_search()``: the architecture model (so the matrix
#: cannot self-validate) and every Markdown file (so ``board.md`` and the cards
#: resolve nothing). Everything else tracked is in domain.
EXCLUDED_PREFIX = "meta/architecture/"
EXCLUDED_SUFFIX = ".md"

#: Directories whose contents are *code* — a mention here is at least a mention
#: by the thing under test. Everything tracked and in domain that is **not**
#: under one of these is pipeline bookkeeping, and a ref kept alive only by
#: those is what this module detects. ``meta/ops`` is here because a ``test:``
#: value may legitimately name a script in it (FR-013's sweep).
CODE_ROOTS = (
    "src/",
    "tests/",
    "player/",
    "scripts/",
    "migrations/",
    "nonogram-web/",
    "meta/ops/",
)

#: ``git grep -w``'s notion of a word character, which is also Python's
#: ``[A-Za-z0-9_]`` and **includes the underscore** — the hole that makes
#: ``git grep -w PropertyTest_Foo`` miss ``def test_PropertyTest_Foo``.
WORD = "A-Za-z0-9_"

_IDENTIFIER = re.compile(rf"[A-Za-z_][{WORD}]*\Z")
_NODE_ID = re.compile(rf"[\w./-]+\.py::[A-Za-z_][{WORD}]*\Z")
_FILE_PATH = re.compile(r"[\w./-]+\.(?:py|sh)\Z")

_DEFINITION = re.compile(rf"^[ \t]*(?:def|class)[ \t]+([A-Za-z_][{WORD}]*)")

FORM_BARE = "bare"
FORM_NODE_ID = "nodeid"
FORM_PATH = "path"

# --- the four authorities that declare a verifying ref ----------------------
# Every one of them is read here, because a ref the guard does not enumerate is
# a ref it cannot report, and the EC is about the whole board. The shapes are
# deliberately matched narrowly: an unrecognised one raises rather than being
# skipped (ADR-0039/R2), and :func:`test_every_declared_check_is_classified`
# is the control for that.

_ADR_CHECK = re.compile(
    r"^[ \t]*check:[ \t]*\{kind:[ \t]*(?P<kind>[a-z-]+)(?:,[ \t]*ref:[ \t]*(?P<ref>[^}]*))?\}",
    re.MULTILINE,
)
_BLOCK_CHECK = re.compile(r"^[ \t]*check:[ \t]*$")
_BLOCK_KIND = re.compile(r"^[ \t]*kind:[ \t]*(?P<kind>[a-z-]+)[ \t]*$")
_BLOCK_REF = re.compile(r"^[ \t]*ref:[ \t]*(?P<ref>.+?)[ \t]*$")
_TEST_KEY = re.compile(r"^[ \t]*test:[ \t]*(?P<ref>.+?)[ \t]*$")
_TESTS_INLINE = re.compile(r"^[ \t]*tests:[ \t]*\[(?P<refs>.*)\][ \t]*$")
_TESTS_BLOCK = re.compile(r"^[ \t]*tests:[ \t]*$")
_LIST_ITEM = re.compile(r"^[ \t]*-[ \t]*(?P<ref>.+?)[ \t]*$")


class RefShapeNotClassifiable(AssertionError):
    """A declared check or ref whose shape this module cannot read.

    Its own exception type because ADR-0039/R2 makes it a **failure** and not a
    quiet pass: a guard that silently ignores a shape it does not understand
    reports a clean board for the one case it was built to catch.
    """


def _split(raw: str) -> list[str]:
    """One ``ref:``/``test:`` value into the names it declares.

    The model's convention is a comma-separated list (it is what
    ``validators/utils.split_check_ref`` accepts), so the split is the same one
    the validator makes; quoting is stripped because YAML allows either form.
    """
    return [piece.strip().strip("'\"").strip() for piece in raw.split(",") if piece.strip()]


@dataclass(frozen=True)
class Declared:
    """One verifying ref, with where the model declares it."""

    ref: str
    sources: tuple[str, ...]

    @property
    def form(self) -> str:
        """``nodeid`` / ``path`` / ``bare``, or raise.

        Order matters: a node id contains a path, so it is tested first.
        """
        if _NODE_ID.match(self.ref):
            return FORM_NODE_ID
        if _IDENTIFIER.match(self.ref):
            return FORM_BARE
        if _FILE_PATH.match(self.ref):
            return FORM_PATH
        raise RefShapeNotClassifiable(
            f"{self.ref!r} (declared by {', '.join(self.sources)}) is neither a "
            "bare name, a pytest node id, nor a tracked script path -- this "
            "guard cannot resolve it either way, which ADR-0039/R2 makes a "
            "failure rather than a silent pass"
        )


def _declared_refs() -> tuple[Declared, ...]:
    """Every verifying ref the model carries, derived from all four authorities.

    Never a written-down list: the whole point of G-2 is that a list of refs in
    this file would revive them. An authority that is missing from disk, or a
    ``check:`` whose shape cannot be read, raises.
    """
    sources: dict[str, set[str]] = {}

    def add(raw: str, source: str) -> None:
        for name in _split(raw):
            sources.setdefault(name, set()).add(source)

    adrs = sorted(ADR_DIR.glob("*.md"))
    if not adrs:
        raise AssertionError(f"no ADR found under {ADR_DIR} -- the ref set cannot be derived")
    for adr in adrs:
        for match in _ADR_CHECK.finditer(adr.read_text(encoding="utf-8")):
            if match.group("kind") != "test":
                continue
            ref = match.group("ref")
            if not ref or not _split(ref):
                raise RefShapeNotClassifiable(
                    f"{adr.name}: a check of kind 'test' declares no resolvable ref: "
                    f"{match.group(0)!r}"
                )
            add(ref, f"adr/{adr.name}")

    for path, label in ((REQUIREMENTS, "requirements.yml"), (TRACE, "trace.yml")):
        if not path.is_file():
            raise AssertionError(f"{path} is missing -- the ref set cannot be derived")

    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        key = _TEST_KEY.match(line)
        if key:
            add(key.group("ref"), "requirements.yml (test:)")
        if _BLOCK_CHECK.match(line):
            add(*_block_check(lines, index))

    lines = TRACE.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        inline = _TESTS_INLINE.match(line)
        if inline:
            add(inline.group("refs"), "trace.yml")
        elif _TESTS_BLOCK.match(line):
            cursor = index + 1
            while cursor < len(lines):
                item = _LIST_ITEM.match(lines[cursor])
                if not item:
                    break
                add(item.group("ref"), "trace.yml")
                cursor += 1

    return tuple(
        Declared(ref, tuple(sorted(sources[ref]))) for ref in sorted(sources)
    )


def _block_check(lines: list[str], index: int) -> tuple[str, str]:
    """The ``ref:`` of a block-form ``check:`` at ``lines[index]``.

    ``requirements.yml``'s INV/CON entries write the check over three lines
    rather than inline as the ADRs do. A block of kind ``test`` with no ``ref:``
    raises; a block of any other kind contributes nothing and returns an empty
    value, which :func:`_split` drops.
    """
    window = lines[index + 1 : index + 5]
    kind = next((m.group("kind") for m in map(_BLOCK_KIND.match, window) if m), None)
    if kind is None:
        raise RefShapeNotClassifiable(
            f"requirements.yml:{index + 1}: a block-form check: declares no kind -- "
            f"window {window!r}"
        )
    if kind != "test":
        return "", "requirements.yml (check:)"
    ref = next((m.group("ref") for m in map(_BLOCK_REF.match, window) if m), None)
    if ref is None:
        raise RefShapeNotClassifiable(
            f"requirements.yml:{index + 1}: a block-form check of kind 'test' "
            f"declares no ref -- window {window!r}"
        )
    return ref, "requirements.yml (check:)"


# --- the two resolvers ------------------------------------------------------


def _git(*args: str) -> str:
    """``git`` in this working tree, or a failure.

    Never three-valued. ``validators/utils`` is right to treat a broken search
    as its own state rather than as an answer, but *here* the only honest
    reaction to a broken instrument is to red: a guard that reports a clean
    board because ``git`` fell over is the same failure as the one it detects.
    """
    done = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=180
    )
    if done.returncode not in (0, 1):
        raise AssertionError(
            f"git {' '.join(args)} failed with {done.returncode}: {done.stderr.strip()!r}"
        )
    return done.stdout


def _in_domain_files() -> tuple[str, ...]:
    """Tracked files the validator's search can see, as repo-relative paths.

    ``git ls-files`` with the two excludes applied here rather than as a
    pathspec, so the exclusion rule is visible in this file and testable
    (:func:`test_the_search_domain_excludes_the_model_and_every_markdown_file`).
    """
    listed = tuple(
        name
        for name in _git("ls-files", "-z").split("\0")
        if name
        and not name.startswith(EXCLUDED_PREFIX)
        and not name.endswith(EXCLUDED_SUFFIX)
    )
    if not listed:
        raise AssertionError("git ls-files named no in-domain file -- nothing was searched")
    return listed


def _trie_pattern(names: tuple[str, ...]) -> re.Pattern[str]:
    """One regex matching any of ``names`` with ``git grep -w``'s boundaries.

    A trie rather than a flat alternation: a flat ``a|b|c`` of this board's ~600
    refs over ~100 MB of tracked text is minutes, the trie is seconds, and the
    suite has to pay the cost on every run.

    The optional tail is wrapped in a group **deliberately**. Written as
    ``body + "?"`` the ``?`` binds to the last character only, and the measured
    effect was three refs silently losing every one of their hits -- a ref whose
    name is a prefix of another ref's. That is precisely the shape of failure
    this module exists to catch, so it gets a control:
    :func:`test_the_loose_resolver_agrees_with_git_grep_itself`.
    """
    root: dict[str, object] = {}
    for name in names:
        node = root
        for character in name:
            node = node.setdefault(character, {})  # type: ignore[assignment]
        node[""] = True  # type: ignore[index]

    def render(node: dict[str, object]) -> str:
        terminal = "" in node
        branches = [
            re.escape(character) + render(child)  # type: ignore[arg-type]
            for character, child in sorted(node.items())
            if character != ""
        ]
        if not branches:
            return ""
        body = branches[0] if len(branches) == 1 else "(?:" + "|".join(branches) + ")"
        return f"(?:{body})?" if terminal else body

    return re.compile(rf"(?<![{WORD}])(?:{render(root)})(?![{WORD}])")


@lru_cache(maxsize=1)
def _loose_resolution() -> dict[str, tuple[str, ...]]:
    """``ref -> the in-domain files that resolve it``, the validator's way.

    An independent reimplementation of
    ``git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'``
    for every ref in one pass. Equivalent by construction: ``-w`` demands a
    non-word character (or an edge) on both sides of the whole pattern, which is
    exactly the lookaround :func:`_trie_pattern` emits, and the match is on raw
    bytes-as-text with no notion of syntax -- comments, docstrings and YAML
    prose all count, which is the entire defect.
    """
    refs = tuple(declared.ref for declared in _declared_refs())
    pattern = _trie_pattern(refs)
    found: dict[str, set[str]] = {ref: set() for ref in refs}
    for name in _in_domain_files():
        try:
            text = (REPO_ROOT / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Tracked but unreadable: it cannot be established that this file
            # does NOT resolve a ref, and a silent drop here would understate
            # the loose side -- i.e. fail open, exactly the wrong direction.
            raise AssertionError(f"{name} is tracked and in domain but could not be read")
        for match in pattern.finditer(text):
            found[match.group(0)].add(name)
    return {ref: tuple(sorted(hits)) for ref, hits in found.items()}


@lru_cache(maxsize=1)
def _definitions() -> dict[str, tuple[str, ...]]:
    """``symbol -> the ``file:line`` of every ``def``/``class`` defining it``.

    One ``git grep`` over the same domain. The regex is POSIX ERE, which is what
    ``git grep`` uses: ``\\b`` is **undefined** there and silently matches
    nothing, which produced a census in which every ref on the board looked
    undefined -- including ones verified by hand minutes earlier. Character
    classes only, therefore, and the control is
    :func:`test_the_definition_search_finds_a_definition_known_to_exist`.
    """
    out: dict[str, set[str]] = {}
    found = _git(
        "grep",
        "-nE",
        r"^[[:space:]]*(def|class)[[:space:]]+[A-Za-z_]",
        "--",
        ".",
        f":(exclude){EXCLUDED_PREFIX.rstrip('/')}",
        f":(exclude)*{EXCLUDED_SUFFIX}",
    )
    for line in found.splitlines():
        name, _, rest = line.partition(":")
        number, _, text = rest.partition(":")
        match = _DEFINITION.match(text)
        if match:
            out.setdefault(match.group(1), set()).add(f"{name}:{number}")
    if not out:
        raise AssertionError("no def/class line was found at all -- the search is broken")
    return {symbol: tuple(sorted(sites)) for symbol, sites in out.items()}


def _strict_resolution(declared: Declared) -> tuple[str, ...]:
    """Where ``declared`` resolves to a real **definition**, by its form.

    * ``nodeid`` -- the named module must carry ``def``/``class <name>``. The
      path is part of the ref, so a definition of the same name in some other
      module does not resolve it.
    * ``path`` -- the named file is tracked.
    * ``bare`` -- some definition's name *contains* the ref. A substring and not
      an equality, because ``_`` is a word character and this board's convention
      is ``def test_PropertyTest_Foo`` for a ref ``PropertyTest_Foo``.
    """
    form = declared.form
    if form == FORM_NODE_ID:
        path, _, name = declared.ref.partition("::")
        return tuple(
            site for site in _definitions().get(name, ()) if site.rsplit(":", 1)[0] == path
        )
    if form == FORM_PATH:
        return (declared.ref,) if declared.ref in _in_domain_files() else ()
    return tuple(
        sorted(
            site
            for symbol, sites in _definitions().items()
            if declared.ref in symbol
            for site in sites
        )
    )


@dataclass(frozen=True)
class Verdict:
    """One ref, resolved both ways."""

    declared: Declared
    loose: tuple[str, ...]
    strict: tuple[str, ...]

    @property
    def ref(self) -> str:
        return self.declared.ref

    @property
    def falsely_alive(self) -> bool:
        """The validator reports it checked; nothing defines it."""
        return bool(self.loose) and not self.strict

    @property
    def falsely_dead(self) -> bool:
        """The validator reports it dead; a definition exists."""
        return not self.loose and bool(self.strict)

    @property
    def bookkeeping_only(self) -> bool:
        """Alive, undefined, and **no code file mentions it at all**.

        The gate's class. For a ref in it, every file the validator's search
        found is one of the pipeline writers in the module docstring: a review
        report, a duration log, the dispatcher's state log, the scored backlog.
        Nothing under ``src/``, ``tests/`` or the other code roots names it even
        in prose, so there is no reading under which the model's claim that it
        is mechanically checked is true.
        """
        return self.falsely_alive and not any(
            hit.startswith(CODE_ROOTS) for hit in self.loose
        )


@lru_cache(maxsize=1)
def _verdicts() -> tuple[Verdict, ...]:
    """Every declared ref, resolved both ways, in ref order."""
    loose = _loose_resolution()
    return tuple(
        Verdict(declared, loose[declared.ref], _strict_resolution(declared))
        for declared in _declared_refs()
    )


def _fingerprint(refs: tuple[str, ...]) -> str:
    """A short digest of a sorted ref class.

    The baselines below are a count and one of these, **never a ref list**: a
    list would spell the dead refs into tracked, non-Markdown code and revive
    every one of them -- the defect, re-created by its own detector (G-2). A
    digest pins the class exactly and resolves nothing.
    """
    joined = "\n".join(sorted(refs)).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:16]


def _report(verdicts: tuple[Verdict, ...]) -> str:
    """A ref class, spelled out for a human. Derived, so it is safe to print."""
    return "\n".join(
        f"  {verdict.ref}\n"
        f"      declared by : {', '.join(verdict.declared.sources)}\n"
        f"      resolved by : {', '.join(verdict.loose) or '(nothing)'}\n"
        f"      defined at  : {', '.join(verdict.strict) or '(nowhere)'}"
        for verdict in verdicts
    )


# --- measured baselines -----------------------------------------------------
# Counts and digests, measured on main at f64112f2 by running this module. They
# are deliberately exact rather than ceilings: "a falling warning count is not
# evidence of repair, and may be evidence of signal loss", so a class SHRINKING
# has to be read and re-derived against a def/class exactly as a class growing
# does. Either direction reds and prints the current class in full.

#: Refs kept alive solely by pipeline bookkeeping -- the gate's class.
BOOKKEEPING_ONLY = (13, "f10ea23d3f456cba")

#: Refs the validator reports checked while nothing defines them. A superset of
#: the above: the rest are mentioned by a comment or docstring under ``tests/``,
#: which is the limit case no pathspec can exclude.
FALSELY_ALIVE = (164, "47dac2b0c321ceeb")

#: Refs the validator reports DEAD while a definition exists -- the other
#: direction, not folded into the first (EC).
FALSELY_DEAD = (13, "2943a2e06c8d35ff")

#: Refs both resolvers agree are absent: an honest gap, and the only class that
#: reads correctly today.
HONEST_DEAD = (30, "cc5207403de4ae67")

#: Node-id refs whose test REALLY EXISTS and whose loose resolution comes from
#: nowhere near it -- the module holding the ``def`` does not spell the
#: ``path::name`` string, so the only reason the validator reads the ref as
#: checked is that some review report, duration log or scored-backlog row
#: happens to quote it. Measured on this board: 4, of which 3 are
#: ``tests/test_player_bundle.py``'s, resolved by **exactly two CARD-218 review
#: YAMLs and nothing else**.
#:
#: This is the *third* shape of the same defect and the one CARD-307 repairs:
#: the refs read as checked today, nothing is wrong with the tests, and pruning
#: two files in ``meta/review/`` would turn all three DEAD without a line of
#: code changing. A docstring node-id table in that module -- the
#: ``tests/test_public_player.py`` / ``tests/test_approval_guess_gate.py``
#: precedent -- moves them into :data:`SAME_FILE_PROSE` and makes them
#: self-resolving. Pinned here so the class cannot grow unnoticed, and so that
#: when CARD-307 shrinks it the shrink has to be read.
RESOLVED_FROM_AFAR = (4, "358bfdc4de982d83")

#: Node-id refs that are defined in the module they name AND also mentioned in
#: that module's prose -- AC-3's edge, and the board's one honest shim: a
#: deliberate docstring node-id table paired with a two-direction guard holding
#: the table to the registry (``tests/test_approval_guess_gate.py``,
#: ``tests/test_public_player.py``, ``tests/test_public_player_pages.py``,
#: ``tests/test_nfr001_generation_time.py``). Pinned because without it the
#: edge test below is satisfied by an EMPTY intersection: measured, the mutant
#: that deletes one of these ``def`` lines made that ref drop out of the set and
#: the test went green on the remaining members. A class whose membership is not
#: pinned cannot witness a member leaving it.
SAME_FILE_PROSE = (16, "5539b351de2562fb")


def _class_of(predicate) -> tuple[Verdict, ...]:
    return tuple(verdict for verdict in _verdicts() if predicate(verdict))


def _assert_class(label: str, baseline: tuple[int, str], members: tuple[Verdict, ...]) -> None:
    refs = tuple(verdict.ref for verdict in members)
    actual = (len(refs), _fingerprint(refs))
    assert actual == baseline, (
        f"the {label!r} class moved: measured {actual}, baseline {baseline}.\n"
        f"This is not automatically a regression and not automatically a repair "
        f"-- re-derive each ref against a def/class before updating the baseline, "
        f"because a class that shrinks because a review report was synced in is "
        f"signal loss, not a fix.\nOnce re-derived, the line to paste is\n"
        f"    {label.replace('-', '_').upper()} = {actual!r}\n"
        f"The class as it stands:\n{_report(members)}"
    )


# --- AC-2 / the gate --------------------------------------------------------


def test_no_verifying_ref_is_resolved_only_by_pipeline_bookkeeping() -> None:
    """AC-2. A ref alive only because the pipeline wrote its name down.

    Reds on any ref that the validator's loose search resolves, that no
    ``def``/``class`` defines, and that no file under a code root mentions at
    all -- so the only things keeping it alive are the review-YAML sync, a
    duration log, ``dispatcher.state`` or the scored backlog. For such a ref the
    model reads as mechanically checked and there is no sense in which it is.

    Pinned as a count and a digest, both derived; the message names every member
    and what resolved it, which is what AC-2 asks for.
    """
    members = _class_of(lambda v: v.bookkeeping_only)
    # The predicate is "no CODE root mentions it"; the class is NAMED for
    # pipeline bookkeeping. Those coincide today and nothing guarantees it:
    # `silhouette/`, `pictures/`, `docs/` and `.claude/` are tracked, in domain
    # and under no code root, so a ref resolved only from one of them would be a
    # true positive carrying a false label. Asserted rather than assumed, so the
    # name cannot quietly stop describing the members.
    strays = {
        hit
        for verdict in members
        for hit in verdict.loose
        if not hit.startswith("meta/")
    }
    assert not strays, (
        f"the bookkeeping-only class has members resolved from outside meta/: "
        f"{sorted(strays)}. They are still refs with no definition, but the "
        f"class name no longer describes them -- rename it or split it."
    )
    _assert_class("bookkeeping-only", BOOKKEEPING_ONLY, members)


def test_the_two_directions_of_disagreement_are_exactly_the_measured_ones() -> None:
    """The EC. Both directions, neither dropped, neither folded into the other.

    ``falsely alive`` is the erosion. ``falsely dead`` is the complementary
    hole: ``-w`` counts ``_`` as a word character and a node id is not an
    identifier, so a perfectly real test reads as a dead ref. The validator
    cannot distinguish either case from the honest one; this assertion is where
    the board records that it knows how many of each it has.
    """
    _assert_class("falsely-alive", FALSELY_ALIVE, _class_of(lambda v: v.falsely_alive))
    _assert_class("falsely-dead", FALSELY_DEAD, _class_of(lambda v: v.falsely_dead))
    _assert_class(
        "honest-dead",
        HONEST_DEAD,
        _class_of(lambda v: not v.loose and not v.strict),
    )


def test_a_node_id_ref_resolved_only_from_outside_its_own_module_is_pinned() -> None:
    """CARD-307's class: the test exists, and bookkeeping is why it reads alive.

    Not a disagreement between the two resolvers -- both say alive -- so it is
    outside the EC's two directions and would otherwise go unrecorded. It is
    still the erosion: the loose resolution rests entirely on files that are
    about the card rather than about the code, and the board has no control
    stopping them being pruned.
    """
    members = tuple(
        verdict
        for verdict in _verdicts()
        if verdict.declared.form == FORM_NODE_ID
        and verdict.strict
        and verdict.ref.partition("::")[0] not in verdict.loose
    )
    _assert_class("resolved-from-afar", RESOLVED_FROM_AFAR, members)
    # The sharp half: for at least one of them NOTHING but review YAMLs
    # resolves the ref. That is the case a reader will not believe without it
    # being asserted, and it is the one CARD-307 exists for.
    review_only = [
        verdict.ref
        for verdict in members
        if verdict.loose and all(hit.startswith("meta/review/") for hit in verdict.loose)
    ]
    assert len(review_only) >= 3, (
        f"expected at least three node-id refs resolved by review reports alone; "
        f"found {review_only}"
    )


def test_every_declared_ref_lands_in_exactly_one_class() -> None:
    """The partition is total: no ref is counted twice and none is lost.

    Without this, the three pinned classes could each be right while a ref
    quietly belonged to none of them -- which is how a derived guard comes to
    report a clean board.
    """
    classes = [
        [v.ref for v in _verdicts() if v.loose and v.strict],
        [v.ref for v in _verdicts() if v.falsely_alive],
        [v.ref for v in _verdicts() if v.falsely_dead],
        [v.ref for v in _verdicts() if not v.loose and not v.strict],
    ]
    flat = [ref for group in classes for ref in group]
    assert len(flat) == len(set(flat)) == len(_verdicts()), (
        f"the partition is not a partition: {len(flat)} memberships over "
        f"{len(set(flat))} distinct refs and {len(_verdicts())} declared refs"
    )


# --- AC-4 / the live instances ----------------------------------------------
# Both refs are spelled in pieces joined at run time, so that neither appears in
# this file as the whole token the loose search matches (G-2). The property is
# not left to care: test_this_module_resolves_no_verifying_ref_at_all asserts it
# over every ref in the model.

#: NFR-001/AC-038's ref -- the permanent case. Its warning was retired by the
#: CARD-301 cycle-1 review report alone, and the test it names has never
#: existed. Confirmed at f64112f2: no ``def`` and no ``class`` anywhere, and
#: exactly two resolvers, one of them ``meta/kanban/dispatcher.state`` -- which
#: the orchestrator wrote while recording this defect.
_AC038_REF = "TestGenerate_50x50_" + "RespectsTimeoutBound"

#: A node-id instance of the same class. AC-4 as drafted named
#: ``tests/test_approval_guess_gate.py::test_unknown_verdict_…closed``
#: (CARD-291's), and that ref has since been **repaired**: CARD-291 merged, the
#: ``def`` is in the named module, and it now resolves both ways. Rather than
#: weaken the assertion, this pins a ref still in the class -- FR-045/AC-392's,
#: resolved by three CARD-218/CARD-284 review reports and nothing else.
_AC392_REF = "tests/test_public_player_pages.py" + "::" + "test_no_homegrown_tracking"


def test_the_permanently_eroded_instance_is_detected() -> None:
    """AC-4, first half: a ref that never landed, kept alive by bookkeeping."""
    eroded = {verdict.ref: verdict for verdict in _class_of(lambda v: v.bookkeeping_only)}
    assert _AC038_REF in eroded, (
        f"{_AC038_REF} is no longer detected as bookkeeping-only. If it gained a "
        f"real definition that is a repair and this test should pin another "
        f"member of the class by name; if it lost its declaration in the model "
        f"the warning is gone for the wrong reason."
    )
    verdict = eroded[_AC038_REF]
    assert not verdict.strict, f"expected no definition, found {verdict.strict}"
    assert any("dispatcher.state" in hit for hit in verdict.loose), (
        f"the orchestrator's own state log is expected among its resolvers; "
        f"resolved by {verdict.loose}"
    )


def test_the_node_id_eroded_instance_is_detected() -> None:
    """AC-4, second half: the same class reached through a node-id ref.

    A detector that only catches the bare-name case would read as working while
    the node-id case erodes every wave, and the node-id form is the one the
    board is migrating to (CARD-294, CARD-291, CARD-307).
    """
    eroded = {verdict.ref: verdict for verdict in _class_of(lambda v: v.bookkeeping_only)}
    assert _AC392_REF in eroded, (
        f"{_AC392_REF} is no longer detected as bookkeeping-only -- re-derive it "
        f"before updating this test"
    )
    verdict = eroded[_AC392_REF]
    assert not verdict.strict, f"expected no definition, found {verdict.strict}"
    assert all(hit.startswith("meta/review/") for hit in verdict.loose), (
        f"expected the review-YAML sync to be its only resolver; resolved by "
        f"{verdict.loose}"
    )


# --- AC-3 / the guard does not absorb honest refs ---------------------------


def test_a_ref_with_a_real_definition_is_not_reported() -> None:
    """AC-3, first half.

    Derived rather than exemplified: *every* ref that resolves to a real
    ``def``/``class`` must be outside both the gate's class and the
    falsely-alive class. The count is asserted so the claim cannot be satisfied
    by an empty set.
    """
    defined = [verdict for verdict in _verdicts() if verdict.strict]
    assert len(defined) > 300, f"only {len(defined)} refs resolve to a definition"
    absorbed = [v.ref for v in defined if v.falsely_alive or v.bookkeeping_only]
    assert not absorbed, f"refs with a real definition were reported anyway: {absorbed}"


def test_a_ref_whose_only_prose_hit_shares_its_definitions_file_stays_green() -> None:
    """AC-3's edge, and the one a naive implementation gets wrong.

    CARD-301 left one prose line naming its own node id in the module that also
    holds the ``def``: measured there, excluding the module holding the ``def``
    still left ``git grep -lw`` exiting 0. A tempting shortcut is to call a hit
    honest when it shares a file with a plausible definition -- that keeps this
    ref green for the wrong reason, and stays green when the ``def`` is deleted.

    So the claim is sharper than "it stays green": a ref in this shape must be
    green **because a definition was found**, and its own file's prose must not
    be what makes it so. Both halves are asserted, and the edge mutant for this
    test is deleting that ``def``.
    """
    same_file = [
        verdict
        for verdict in _verdicts()
        if verdict.declared.form == FORM_NODE_ID
        and verdict.strict
        and verdict.ref.partition("::")[0] in verdict.loose
    ]
    assert same_file, (
        "no node-id ref has a prose mention in the same module as its "
        "definition -- AC-3's edge is unexercised and this test proves nothing"
    )
    _assert_class("same-file-prose", SAME_FILE_PROSE, tuple(same_file))
    for verdict in same_file:
        assert not verdict.falsely_alive and not verdict.bookkeeping_only, (
            f"{verdict.ref} was reported despite being defined at {verdict.strict}"
        )
        module = verdict.ref.partition("::")[0]
        assert any(site.rsplit(":", 1)[0] == module for site in verdict.strict), (
            f"{verdict.ref} is green but not because of a definition in {module}: "
            f"defined at {verdict.strict}"
        )


# --- G-2 / this module revives nothing --------------------------------------


def test_this_module_resolves_no_verifying_ref_at_all() -> None:
    """G-2. The detector is not one of the resolvers it detects.

    The interesting cell. A guard that names dead refs puts their strings into
    tracked, non-Markdown code -- and ``tests/`` is in domain -- so it revives
    them through the very mechanism it exists to catch, and the next validator
    run reports them checked.

    Asserted over **every** ref in the model rather than over the two this file
    names. CARD-291's cycle-1 reviewer split one token, verified the split, and
    still revived refs: the ones it had not thought about. A per-ref check that
    only covers the refs you remembered is the check that already failed.
    """
    this_file = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()
    # Applied to this file's text directly, NOT through _loose_resolution()'s
    # tracked-file pass. git ls-files cannot see an untracked file, so routing
    # the self-check through the tracked domain would make it pass vacuously for
    # exactly as long as the file is new -- which is the window in which the
    # mistake gets made. Measured: before this was changed, the test passed on an
    # uncommitted file that it had not read.
    refs = tuple(declared.ref for declared in _declared_refs())
    pattern = _trie_pattern(refs)
    resolved = sorted(
        {match.group(0) for match in pattern.finditer(Path(__file__).read_text(encoding="utf-8"))}
    )
    assert not resolved, (
        f"{this_file} resolves {len(resolved)} verifying ref(s) and so revives "
        f"them for the validator: {resolved}. Spell them in pieces joined at run "
        f"time, or derive them instead of naming them."
    )
    # And the same once it is tracked, which is the state that actually feeds
    # the validator.
    assert this_file not in {
        hit for hits in _loose_resolution().values() for hit in hits
    }, f"{this_file} is a tracked resolver of at least one verifying ref"


def test_the_two_pinned_refs_are_spelled_in_pieces() -> None:
    """The control for the cell above: the split is real, not incidental.

    Without this, :func:`test_this_module_resolves_no_verifying_ref_at_all`
    would also pass on a file that happens to name no ref, and would stop being
    evidence that the splitting technique is what makes it pass.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    for ref in (_AC038_REF, _AC392_REF):
        assert ref in _loose_resolution(), f"{ref} is not a ref declared by the model"
        assert ref not in source, (
            f"{ref} appears in this file as a whole token -- the split was lost "
            f"and this file now resolves it"
        )
        head = ref.split("_")[0] if "::" not in ref else ref.partition("::")[0]
        assert head in source, (
            f"{ref} is not spelled in pieces here either -- it is not pinned by "
            f"name at all, so AC-4's assertion is vacuous"
        )


# --- instrument controls ----------------------------------------------------
# A crashing or empty-selecting instrument reports NOT-REACHED, which is
# indistinguishable from a clean board. Each resolver gets a control that would
# fail if it answered nothing.


def test_the_loose_resolver_agrees_with_git_grep_itself() -> None:
    """The reimplementation is checked against the real ``git grep -lw``.

    Not on every ref -- that is ~600 subprocesses -- but on a derived sample
    that is guaranteed to contain the interesting shapes: every member of the
    gate's class, every falsely-dead ref, and every ref whose name is a prefix
    of another ref's. That last group is the one the trie's ``?``-binding bug
    silently emptied, and it is why this control exists at all.
    """
    loose = _loose_resolution()
    refs = sorted(loose)
    prefixes = {
        ref
        for index, ref in enumerate(refs)
        for other in refs[index + 1 :]
        if other.startswith(ref)
    }
    sample = sorted(
        {verdict.ref for verdict in _class_of(lambda v: v.bookkeeping_only)}
        | {verdict.ref for verdict in _class_of(lambda v: v.falsely_dead)}
        | prefixes
    )
    assert len(sample) >= 20, f"the sample is too small to prove anything: {sample}"
    assert prefixes, "no prefix-shaped ref pair exists; the trie bug would go unseen"
    for ref in sample:
        found = _git(
            "grep",
            "-lw",
            ref,
            "--",
            ".",
            f":(exclude){EXCLUDED_PREFIX.rstrip('/')}",
            f":(exclude)*{EXCLUDED_SUFFIX}",
        )
        expected = tuple(sorted(line for line in found.splitlines() if line))
        assert loose[ref] == expected, (
            f"the loose reimplementation disagrees with git grep -lw on {ref!r}:\n"
            f"  this module: {loose[ref]}\n  git grep   : {expected}"
        )


def test_the_definition_search_finds_a_definition_known_to_exist() -> None:
    """The POSIX-ERE control. ``\\b`` here matches nothing, silently.

    A first census of this board used ``\\b`` in the definition regex and
    concluded that every ref was undefined -- including ones verified by hand
    minutes earlier -- because ``git grep`` uses POSIX ERE, in which ``\\b`` is
    undefined. The bug bit twice in one session, so the sanity check is a test:
    this module's own function names must be found by the search that is
    supposed to find definitions.
    """
    definitions = _definitions()
    assert len(definitions) > 5000, f"only {len(definitions)} symbols found at all"

    # Cross-checked against a second implementation rather than against a name
    # written down here: Python's own regex over one tracked module's text must
    # agree exactly with what git's ERE found in it. A `\b` in the ERE makes the
    # right-hand side empty while the left-hand side stays full, so the two
    # cannot both be wrong in the same direction.
    probe = "tests/test_cli.py"
    assert probe in _in_domain_files(), f"{probe} is not in the search domain"
    mine = {
        match.group(1)
        for line in (REPO_ROOT / probe).read_text(encoding="utf-8").splitlines()
        for match in [_DEFINITION.match(line)]
        if match
    }
    assert len(mine) >= 20, f"{probe} defines only {len(mine)} symbols by Python's reading"
    by_git = {
        symbol
        for symbol, sites in definitions.items()
        if any(site.rsplit(":", 1)[0] == probe for site in sites)
    }
    assert by_git == mine, (
        f"the ERE definition search and Python disagree on {probe}: "
        f"git-only {sorted(by_git - mine)}, python-only {sorted(mine - by_git)}"
    )


def test_the_search_domain_excludes_the_model_and_every_markdown_file() -> None:
    """The domain is the validator's, not a wider or narrower one.

    If ``meta/architecture/**`` leaked in, every ref would resolve to the file
    declaring it and the whole guard would report a clean board. If ``*.md``
    leaked in, the cards would do the same. If the domain were *narrower* than
    the validator's, the gate would report refs the validator does not.
    """
    domain = _in_domain_files()
    assert len(domain) > 500, f"only {len(domain)} files in domain"
    assert not [name for name in domain if name.startswith(EXCLUDED_PREFIX)]
    assert not [name for name in domain if name.endswith(EXCLUDED_SUFFIX)]
    assert "meta/architecture/requirements.yml" not in domain
    assert "meta/kanban/board.md" not in domain
    # The two that make the pathspec narrowing insufficient, and the one the
    # fourth instance turned up: no .md extension, so it is in domain.
    assert "meta/kanban/dispatcher.state" in domain
    assert any(name.startswith("meta/review/") for name in domain)
    assert any(name.startswith("meta/profiling/") for name in domain)
    assert any(name.startswith("tests/") for name in domain)


# --- ADR-0039/R2 / an unanalysable shape is a failure -----------------------


def test_every_declared_check_is_classified() -> None:
    """Every ref on the board has a form this module can resolve.

    The derivation's completeness claim. ``Declared.form`` raises rather than
    returning a default, so this test reaching the end is the statement that no
    shape was skipped.
    """
    forms = {FORM_BARE: 0, FORM_NODE_ID: 0, FORM_PATH: 0}
    for declared in _declared_refs():
        forms[declared.form] += 1
    assert sum(forms.values()) == len(_declared_refs())
    assert all(count for count in forms.values()), (
        f"a ref form has no instance on this board: {forms} -- either the board "
        f"changed shape or the derivation stopped seeing one"
    )


def test_an_unclassifiable_shape_is_a_failure_and_not_a_pass() -> None:
    """The control for the clause above (ADR-0039/R2).

    Without it, ``Declared.form``'s raise is an unexercised branch and the
    claim "an unanalysable shape is a FAILURE" is a comment.
    """
    for nonsense in ("not a ref at all", "tests/foo.py::", "a-b-c", ""):
        try:
            Declared(nonsense, ("synthetic",)).form
        except RefShapeNotClassifiable:
            continue
        raise AssertionError(f"{nonsense!r} was classified instead of refused")


def test_a_check_of_kind_test_without_a_ref_is_a_failure() -> None:
    """The same, for the block-form ``check:`` in ``requirements.yml``."""
    try:
        _block_check(["    check:", "      kind: test", "      severity: mandatory"], 0)
    except RefShapeNotClassifiable:
        pass
    else:
        raise AssertionError("a kind: test check with no ref: was accepted")
    try:
        _block_check(["    check:", "      severity: mandatory"], 0)
    except RefShapeNotClassifiable:
        pass
    else:
        raise AssertionError("a check with no kind: was accepted")
    assert _block_check(["    check:", "      kind: review-lens"], 0) == (
        "",
        "requirements.yml (check:)",
    ), "a review-lens check must contribute no ref rather than raise"


def test_the_derivation_reads_all_four_authorities() -> None:
    """No authority is silently missing from the ref set.

    A ref declared only in ``trace.yml`` and nowhere else is still a ref the
    validator resolves, and an earlier census of this board missed both
    ``trace.yml`` and ``requirements.yml``'s block-form checks -- 424 refs
    instead of 576, which is a 26 % blind spot in a guard about blind spots.
    """
    sources = {source for declared in _declared_refs() for source in declared.sources}
    assert any(source.startswith("adr/") for source in sources), sources
    assert "requirements.yml (test:)" in sources, sources
    assert "requirements.yml (check:)" in sources, sources
    assert "trace.yml" in sources, sources
    assert len(_declared_refs()) > 500, f"only {len(_declared_refs())} refs derived"
