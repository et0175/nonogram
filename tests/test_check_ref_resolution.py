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
    **191** bare refs therefore have no containing definition, and flagging all
    of them would be a census of a naming convention rather than a detector of
    erosion. (This sentence read 163 until review cycle 1, which is two
    different populations in one number: 191 bare refs have no definition, and
    **163** of those are additionally *loose-alive*, i.e. bare **and** falsely
    alive. Both figures are derived; only the first belongs in this sentence.)

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

**The board's own worst instance of that overstatement is ADR-0006/R1**, and it
is worth spelling out here because this module is where someone will come to
look. Its ref has zero definitions and **110** resolvers, so it is a genuinely
dead pointer and this module reports it. (The figure was 109 at the cut and 110
once ``main`` was merged in -- one more synced review report. A resolver count
that climbs every wave with nothing being written is the mechanism, stated as a
moving number rather than a fixed one, because quoting it as fixed is how it
stops being re-derived.) The **rule** it points at is nevertheless
tested: ``tests/test_export_pdf.py:1249`` asserts the runtime dependency list
equals ``{"pillow", "numpy"}`` exactly, and says in its own docstring that
ADR-0006's revision is what makes it the rule's check rather than one card's
guardrail. The ADR does name that test, in a ``#`` comment inside the excluded
``meta/architecture/**``, where the validator cannot see it. Every earlier
telling on this board implied the dependency baseline itself was unverified; it
is not. *Dead ref* and *untested rule* are different findings, and this module
only ever reports the first.

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
   pieces that are joined at run time, never as a whole token.
   :func:`test_this_module_resolves_no_verifying_ref_at_all` asserts the
   property over **every** ref in the model, not just those two — which is the
   half CARD-291's reviewer did not have, and the reason its careful split
   still made no difference. Measured: on this module's first run that test
   named three refs its own docstring had revived -- which is how ready a
   file written *about* the defect is to commit it.

   **The ellipsis is a convenience and NOT the safety property — the earlier
   wording here had this backwards and the correction matters.** Where this
   module's prose quotes a ref as an example it truncates it with ``…``, and
   the reason given used to be that ``…`` is not a word character so
   ``git grep -w`` cannot complete the token. That is false, and measured false
   in a throwaway repository: ``git grep -lw ZZPrefix`` **matches**
   ``ZZPrefix…Tail``, because a non-word character *terminates* the token and
   therefore exposes every prefix. Truncation revives any ref whose declared
   name is a prefix of the truncation — review cycle 1 planted one and got
   ``1 failed``. What makes the device safe is the self-check in point 2 above,
   which reads this file's own bytes against the whole declared set. The claim
   that matters is the PROPERTY, not a count: **no truncation in this file has a
   declared ref as its prefix**, and the assertion establishes that rather than
   the ellipsis guaranteeing it.

   **The count is deliberately not stated, and that is a finding rather than an
   omission.** Earlier wording here said "0 of the 5 truncations"; review cycle 2
   measured 6 tokens and spent a finding on the ambiguity between "truncations of
   refs", "tokens containing an ellipsis" and "ellipsis characters". Writing the
   measured number back into this docstring **changed it**: the sentence stating
   the figure contained ellipses of its own, so the file went from 8 occurrences
   to 11 and the new sentence was wrong the moment it was written. A figure whose
   act of being stated falsifies it cannot be pinned, and this card is the card
   about stated figures that nothing re-derives -- so the figure is replaced by
   the property, which is derived on every run and cannot drift. It can
   establish it for the same reason the ellipsis fails: :func:`_trie_pattern`
   reproduces ``-w``'s boundaries, so a truncation whose prefix is a declared
   ref matches there exactly as it matches under real ``git grep -lw``.
   Anybody dropping the self-check and keeping the ellipsis keeps the
   appearance and loses the property.

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

import ast
import hashlib
import re
import subprocess
import warnings
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
# a ref it cannot report, and the EC is about the whole board.
#
# The patterns below are deliberately narrow, and "an unrecognised shape raises"
# is TWO claims with two different controls. Review cycle 2 found this comment
# naming one control for both, and the named one could not witness the half that
# mattered -- which is this card's own subject arriving on this card's own code,
# for the second cycle running:
#
# * a ref whose FORM cannot be resolved raises -- :meth:`Declared.form`, whose
#   control is :func:`test_an_unclassifiable_shape_is_a_failure_and_not_a_pass`,
#   with :func:`test_every_declared_check_is_classified` recording that no ref on
#   the board reaches it today;
# * a declaration KEY whose shape none of these patterns claims raises --
#   :func:`_refuse_unread_declaration_keys`, whose control is
#   :func:`test_an_unreadable_declaration_key_shape_is_a_failure_and_not_a_skip`.
#
# ``test_every_declared_check_is_classified`` is NOT the control for the second:
# it iterates the refs the derivation already produced and checks each one's
# form, so a key whose shape was never read contributes no ref for it to look
# at and it stays green. Six YAML-legal ``tests:`` key shapes fell through the
# dispatch exactly that way until review cycle 2 planted one and measured the
# consequence: census unmoved, both readings of ``trace.yml`` agreeing at 510,
# every cell green, and the G-2 self-check's trie -- built FROM the derived set
# -- reporting CLEAN on a text that spelled the planted ref in full.

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
#: A mapping key, which is how a block-form ``tests:`` list legitimately ENDS --
#: the only non-item line that may close one. Everything else between two items
#: is either a classified survivor (comment, blank) or a failure; see
#: :func:`_tests_block`, where a ``break`` on this distinction silently dropped
#: 16 refs.
_MAPPING_KEY = re.compile(
    r"^[ \t]*(?P<key>[A-Za-z_][\w .()/'\"-]*):(?:[ \t](?P<value>.*))?[ \t]*$"
)

#: A **declaration key**, matched loosely on purpose: this is the default-deny
#: half of the derivation and it sits one frame ABOVE :func:`_tests_block`.
#: ``_ADR_CHECK``, ``_BLOCK_CHECK``, ``_TEST_KEY``, ``_TESTS_INLINE`` and
#: ``_TESTS_BLOCK`` are each narrow, and a ``test:``/``tests:``/``check:`` key in
#: any other YAML-legal shape used to fall through all of them and contribute
#: nothing, with no exception and nothing to read -- a multi-line flow sequence
#: (``tests: [A,``), a block scalar (``tests: >-``), a plain scalar
#: (``tests: SomeName``), a comment after the key (``tests: # note``), a trailing
#: comment on an inline list (``tests: [A] # note``), an anchor
#: (``tests: &a``). Two of those six are invisible to
#: :func:`_trace_tests_refs_by_backward_scan` as well, because both readings
#: assume a ref lives either in a flow sequence or in a block sequence of
#: ``- item`` lines; so the cross-reading AGREED at 510 and both were wrong.
#: Every line this pattern matches must be claimed by one of the narrow patterns
#: or :func:`_refuse_unread_declaration_keys` raises. A space or end-of-line
#: after the colon is demanded because that is what makes a YAML mapping key a
#: mapping key. The **quoted** spelling (``"tests": [A]``) is matched too, and
#: that is review cycle 3's F-001c3(d): it matched neither this pattern nor any
#: narrow one, so it was invisible to collection AND to refusal -- F-001c2's
#: asymmetry un-closed for one spelling. It is deliberately made a CANDIDATE
#: rather than taught to the narrow patterns, because this function's own
#: refusal says *"do not widen a narrow pattern until it swallows the shape
#: without reading it"*; a quoted key now raises by name instead of being added
#: to the census unread. **0** quoted declaration keys in any authority today,
#: measured, so this changes nothing on the board and everything on the next
#: edit that introduces one.
_DECLARATION_KEY = re.compile(r"^[ \t]*(?P<q>[\"']?)(?P<key>tests?|check)(?P=q):(?:[ \t].*)?$")

#: A block scalar's opener (``key: >-``, ``key: |``). Its body is **prose**, so
#: a line inside it that looks like a declaration key is not one.
#:
#: The trailing ``(?:#.*)?`` is review cycle 3's F-001c3(a), and it is the
#: sharpest of the four region holes because it fails in the INVENTING
#: direction: ``rationale: >- # a note`` is legal YAML and an earlier version of
#: this pattern demanded end-of-line after the indicator, so the opener was not
#: recognised, its body was not prose, and a body line beginning ``test: `` whose
#: text happens to be an identifier was **silently collected as a declared ref**
#: -- census 4 -> 5 on a synthetic set with nothing raised. The default-deny one
#: frame up cannot catch that direction BY CONSTRUCTION: it fires only where no
#: narrow pattern claims, and invention happens exactly where one does. So the
#: repair has to be in the region notion, which is what this is. **0** such
#: openers in either YAML authority or in the ADR set today, measured.
#:
#: The space before the ``#`` is optional here although YAML demands one, and
#: that is deliberate rather than sloppy: the permissive reading errs toward
#: treating prose AS prose, which is the direction that cannot invent a ref, and
#: it cannot swallow a declaration key either, because
#: :func:`_declaration_key_lines` tests for the KEY before it skips a body. Do
#: not tighten it to ``[ \t]+#`` without a row in the matrix for what that
#: re-opens.
_BLOCK_SCALAR = re.compile(
    r"^(?P<indent>[ \t]*)[^#\s][^:]*:[ \t]*[>|][-+0-9]*[ \t]*(?:#.*)?$"
)

#: A Markdown code fence -- three backticks **or** ``~~~``, which CommonMark
#: treats alike and this module used to know only the first of -- review cycle
#: 3's F-001c3(b): inside a ``~~~`` fence the ADR refusal was silently skipped,
#: so a block-form ``check:`` there contributed nothing and raised nothing,
#: where the same shape one fence character over raises. No ref is dropped by
#: that hole (the ADR scan collects inline checks document-wide), so it loses the
#: REFUSAL rather than a ref -- which is still an ADR-0039/R2 silent skip. The
#: marker character is captured because a fence is closed only by its own
#: character: ``~~~`` inside a backtick-fenced block is content, not a
#: close. **0** ``~~~`` fences in the ADR set today, and all 46 fence lines are
#: exactly three backticks, measured.
_FENCE = re.compile(r"^[ \t]*(?P<marker>`{3,}|~{3,})")


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
    #: Where the model declares it, as ``<authority>:<line>`` -- the LINE and not
    #: just the file, because :attr:`form`'s refusal is the one route in this
    #: module that does not name a line of its own. Review cycle 3 measured all
    #: 20 key-route refusals naming the correct line and all 6 form-route
    #: refusals naming none; for five of those six the refusal quotes a unique
    #: grep handle, but for ``test: >-`` it quotes ``'>-'`` and nothing else,
    #: which on a registry with 152 block scalars is no handle at all. Carrying
    #: the line here closes all six at once, on every authority rather than on
    #: the one whose shapes reach that route today.
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


def _declaration_key_lines(
    lines: list[str], *, fenced: bool, label: str
) -> tuple[int, ...]:
    """Indices of lines on which a declaration key could legitimately live.

    A default-deny is only as good as its notion of *where* a declaration can
    be, and getting that wrong in the loose direction makes the guard red on
    English rather than on a missed ref. Both regions are **measured**, not
    assumed, and the measurement is the reason they exist:

    * ``fenced`` -- the ADRs are Markdown, so only a fenced block declares
      anything. All **68** anchored ``check:`` lines in the ADR set are inside a
      fence. Exactly **one** declaration-key-looking line is outside one, and it
      is English: ``0042-book-interior-is-vector-cover-stays-raster.md:153``
      wraps a sentence onto a line beginning *"tests: its 0.48/1.28/2.08 pt are
      the owner's figures"*. It declares nothing, it arrived with an ordinary ADR
      edit, and a scan without a notion of fences would red the suite on it. So
      the region is part of the rule.
    * the YAML authorities -- everywhere except inside a block scalar, whose body
      is prose for the same reason. Measured: **152** such blocks in
      ``requirements.yml`` and **69** in ``trace.yml``, **2309** body lines
      between them, and **0** of those lines looks like a declaration key today.
      This half therefore changes nothing on today's board and is here because
      the ADR authority proves the shape is not hypothetical; it is carried by a
      synthetic control rather than by a live witness, and that is said rather
      than left for the next reviewer to find.

    **Totality, which review cycle 3 measured and this version repairs.** A
    region notion that both halves of the derivation now rest on is only worth
    what its edges are worth, and four shapes fell off them -- two of those in
    the silent direction, which is this card's whole subject. All four were
    measured LATENT on the real authorities and all four are now classified or
    raising, each with its own row in
    :func:`test_an_unreadable_declaration_key_shape_is_a_failure_and_not_a_skip`:
    a block-scalar opener carrying a trailing YAML comment (invention -- see
    :data:`_BLOCK_SCALAR`), a ``~~~`` fence (silent skip -- see :data:`_FENCE`),
    a quoted declaration key (silent skip both ways -- see
    :data:`_DECLARATION_KEY`), and an **unclosed** fence, which is the one this
    function itself answers: it used to flip the region for the rest of the
    document, so the one live out-of-fence prose line at
    ``0042-book-interior-is-vector-cover-stays-raster.md:153`` became a
    candidate and the guard red on English. Every ADR's fence parity is even
    today, so that was latent only because of an invariant nothing asserted; now
    an unclosed fence is a failure naming the FENCE, which is the shape a human
    can act on, rather than a refusal naming an innocent sentence.
    """
    candidates: list[int] = []
    fence: tuple[str, int] | None = None
    cursor = 0
    while cursor < len(lines):
        raw = lines[cursor]
        marker = _FENCE.match(raw) if fenced else None
        if marker:
            char = marker.group("marker")[0]
            if fence is None:
                fence = (char, cursor)
            elif fence[0] == char:
                fence = None
            cursor += 1
            continue
        if fence is not None or not fenced:
            # The key test comes FIRST: ``tests: >-`` is a declaration key in a
            # block-scalar shape, so it is both a candidate (nothing claims it,
            # so it must raise) and the owner of a body to skip. Testing the
            # block-scalar shape first would have skipped the key itself, which
            # is the same silent-skip bug one more frame out.
            if _DECLARATION_KEY.match(raw):
                candidates.append(cursor)
            opener = _BLOCK_SCALAR.match(raw)
            if opener:
                base = len(opener.group("indent").expandtabs(8))
                cursor += 1
                while cursor < len(lines):
                    body = lines[cursor]
                    if body.strip() and (
                        len(body[: len(body) - len(body.lstrip(" \t"))].expandtabs(8)) <= base
                    ):
                        break
                    cursor += 1
                continue
        cursor += 1
    if fence is not None:
        raise RefShapeNotClassifiable(
            f"{label}:{fence[1] + 1}: this {fence[0] * 3} code fence is never "
            f"closed, so every line from here to the end of the file reads as "
            f"INSIDE a fence -- which turns ordinary ADR prose that happens to "
            f"wrap onto a line beginning 'tests:' into a declaration key and "
            f"reds this guard on English (the live shape is "
            f"0042-book-interior-is-vector-cover-stays-raster.md:153). The "
            f"region is part of the rule (ADR-0039/R2), so a region this module "
            f"cannot determine is a FAILURE naming the fence, not a refusal "
            f"naming an innocent sentence. Close the fence."
        )
    return tuple(candidates)


def _refuse_unread_declaration_keys(
    label: str, lines: list[str], unread: tuple[int, ...]
) -> None:
    """Default-deny on the declaration KEY itself (ADR-0039/R2), one frame up.

    :func:`_tests_block` is total for the lines *inside* a block sequence --
    review cycle 2 drove fourteen shapes at it and every one is collected or
    raises. The hole it found is the frame that decides whether ``_tests_block``
    is entered at all: a ``tests:`` key was read only if it was a complete
    single-line flow sequence or a bare key, and every other YAML-legal shape of
    the same key fell through both branches and contributed nothing. That is
    cycle 1's defect verbatim, moved up one frame, and it is why this function
    exists on **all four** authorities rather than on the one that was caught.

    **Why no pinned count could have caught it, and therefore why nothing is
    pinned instead of this raise.** :data:`CENSUS` pins what *is* derived, not
    what is missed. CONVERTING an existing list into an unreadable shape drops
    refs and reds :data:`CENSUS`; ADDING a ref in an unreadable shape is
    silently absent and :data:`CENSUS` does not move -- measured. That asymmetry
    is exactly what let the 576 census sit baselined for a whole cycle.

    ``unread`` is passed in rather than recomputed, because the callers derive
    the lines they READ from :func:`_declaration_key_lines` as well. Both halves
    therefore share one notion of where a declaration can live, and cannot drift
    apart -- which they did in this function's first draft: the narrow
    ``_TEST_KEY`` pattern was still matching every line in the file, so it
    collected a wrapped prose line inside a ``rationale: >-`` block as a ref
    while the default-deny correctly ignored it. A guard that invents a ref out
    of prose corrupts the census in the opposite direction to the one this card
    is about, and it was found by the synthetic authority set in
    :func:`test_an_unreadable_declaration_key_shape_is_a_failure_and_not_a_skip`
    rather than by reasoning.
    """
    if not unread:
        return
    first = unread[0]
    key = _DECLARATION_KEY.match(lines[first])
    raise RefShapeNotClassifiable(
        f"{label}:{first + 1}: {lines[first]!r} is a "
        f"{key.group('key') if key else '?'}: declaration key in a shape no "
        f"pattern in this module claims, so every ref it declares is invisible "
        f"to the derivation -- and to its independent second reading, which "
        f"shares the same assumption about where a ref lives. "
        f"{len(unread)} such line(s) in {label}. ADR-0039/R2 makes an "
        f"unanalysable shape a FAILURE: the alternative is the silent skip that "
        f"kept 16 refs out of the census for a whole review cycle one frame "
        f"below this one, and that no pinned count can see. Teach the "
        f"derivation this shape; do not widen a narrow pattern until it "
        f"swallows the shape without reading it."
    )


def _declared_refs() -> tuple[Declared, ...]:
    """Every verifying ref the model carries, derived from all four authorities.

    Never a written-down list: the whole point of G-2 is that a list of refs in
    this file would revive them. An authority that is missing from disk, a
    ``check:`` whose shape cannot be read, **or a declaration key whose shape no
    pattern here claims**, raises. The last of those three is
    :func:`_refuse_unread_declaration_keys`, and it is the half that was missing:
    each authority's scan records the lines it CLAIMED, and every line that looks
    like a ``test:``/``tests:``/``check:`` key and was claimed by nothing is a
    failure rather than a silent skip.
    """
    sources: dict[str, set[str]] = {}

    def add(raw: str, source: str) -> None:
        for name in _split(raw):
            sources.setdefault(name, set()).add(source)

    adrs = sorted(ADR_DIR.glob("*.md"))
    if not adrs:
        raise AssertionError(f"no ADR found under {ADR_DIR} -- the ref set cannot be derived")
    for adr in adrs:
        document = adr.read_text(encoding="utf-8")
        lines = document.splitlines()
        claimed: set[int] = set()
        for match in _ADR_CHECK.finditer(document):
            # A match may in principle span lines (``[^}]*`` crosses newlines),
            # so every line it covers counts as claimed rather than just its
            # first.
            claimed.update(
                range(
                    document.count("\n", 0, match.start()),
                    document.count("\n", 0, match.end()) + 1,
                )
            )
            if match.group("kind") != "test":
                continue
            line_no = document.count("\n", 0, match.start()) + 1
            ref = match.group("ref")
            if not ref or not _split(ref):
                raise RefShapeNotClassifiable(
                    f"{adr.name}: a check of kind 'test' declares no resolvable ref: "
                    f"{match.group(0)!r}"
                )
            add(ref, f"adr/{adr.name}:{line_no}")
        # The ADRs declare refs ONLY through the inline form. A block-form
        # ``check:`` in one would be read by nothing here, so it raises; 0 ADRs
        # use one today, which is why this is latent and fixed anyway.
        #
        # The asymmetry here is deliberate: ``_ADR_CHECK`` collects from the
        # whole document while the REFUSAL is scoped to fenced regions. So an
        # anchored inline ``check:`` outside a fence is still collected (never
        # skipped) and never raises, while an unreadable shape inside a fence
        # raises. Permissive collection, region-scoped refusal -- the other way
        # round would turn ADR-0042's wrapped prose line into a failure, and
        # scoping collection too would turn an out-of-fence declaration into a
        # silent skip.
        _refuse_unread_declaration_keys(
            f"adr/{adr.name}",
            lines,
            tuple(
                index
                for index in _declaration_key_lines(
                    lines, fenced=True, label=f"adr/{adr.name}"
                )
                if index not in claimed
            ),
        )

    for path, label in ((REQUIREMENTS, "requirements.yml"), (TRACE, "trace.yml")):
        if not path.is_file():
            raise AssertionError(f"{path} is missing -- the ref set cannot be derived")

    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    unread: list[int] = []
    for index in _declaration_key_lines(lines, fenced=False, label="requirements.yml"):
        line = lines[index]
        key = _TEST_KEY.match(line)
        if key:
            add(key.group("ref"), f"requirements.yml:{index + 1} (test:)")
        elif _BLOCK_CHECK.match(line):
            add(*_block_check(lines, index))
        else:
            unread.append(index)
    _refuse_unread_declaration_keys("requirements.yml", lines, tuple(unread))

    lines = TRACE.read_text(encoding="utf-8").splitlines()
    unread = []
    for index in _declaration_key_lines(lines, fenced=False, label="trace.yml"):
        line = lines[index]
        inline = _TESTS_INLINE.match(line)
        if inline:
            add(inline.group("refs"), f"trace.yml:{index + 1}")
        elif _TESTS_BLOCK.match(line):
            for ref in _tests_block(lines, index):
                add(ref, f"trace.yml:{index + 1}")
        else:
            unread.append(index)
    _refuse_unread_declaration_keys("trace.yml", lines, tuple(unread))

    return tuple(
        Declared(ref, tuple(sorted(sources[ref]))) for ref in sorted(sources)
    )


def _tests_block(lines: list[str], index: int) -> tuple[str, ...]:
    """The items of the block-form ``tests:`` list opened at ``lines[index]``.

    Every line after the key is **classified**; nothing is used as a mute stop
    signal. The first draft of this scan stopped at the first line that was not
    a ``- item``, which is wrong on this file and wrong in the direction that
    cannot be noticed: a ``#`` comment *inside* a list ended the list and
    dropped every remaining item with no exception and nothing to read.
    Measured on ``trace.yml``: three such comments -- and all three are notes
    about a **retired** test, i.e. sitting exactly where the interesting refs
    are -- cost 16 of that file's 510 refs, 494 derived instead of 510, and 3
    refs off the whole board's census. ADR-0039/R2 makes an unanalysable shape
    a FAILURE, and ``break`` is not a failure.

    So the four cases are named instead:

    * a ``- item`` indented at least as far as the key -- collected;
    * a blank line or a ``#`` comment -- **surviving**, because YAML ends a
      block sequence at neither;
    * a mapping key at or outside the key's own indentation, or a list item
      dedented past it -- the list legitimately ends;
    * anything else -- :exc:`RefShapeNotClassifiable`, so the next shape this
      file grows is read by a human rather than silently swallowed.

    The count this returns is held against a second, independent reading of the
    same file by
    :func:`test_the_trace_tests_lists_agree_with_an_independent_reading`, which
    is the witness neither of the two older self-checks could be: one compares
    the ref set against itself and the other asserts a floor far below it.

    **What this repair does and does not turn from luck into design.** None of
    the six class baselines moved when the 3 missing refs came back, because all
    3 happen to resolve to a real ``class``. That was luck and it stays luck: it
    is a fact about today's data, not something any code here guarantees, and
    the next silently-dropped ref could as easily have been a dead one sitting
    in the gate's class. What *is* design now is the layer underneath: a line
    this scan cannot classify **raises**, so a drop cannot be silent again; and
    the census and ``trace.yml``'s contribution are pinned exactly and
    cross-read, so a count that moves for any reason -- including the one that
    looked like nothing happening -- reds and has to be read. The honest
    statement is that the fix removes the *silence*, not the luck.
    """
    base = len(lines[index][: len(lines[index]) - len(lines[index].lstrip(" \t"))].expandtabs(8))
    refs: list[str] = []
    for cursor in range(index + 1, len(lines)):
        raw = lines[cursor]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        width = len(raw[: len(raw) - len(raw.lstrip(" \t"))].expandtabs(8))
        item = _LIST_ITEM.match(raw)
        if item:
            if width < base:
                return tuple(refs)
            refs.append(item.group("ref"))
            continue
        if _MAPPING_KEY.match(raw) and width <= base:
            return tuple(refs)
        raise RefShapeNotClassifiable(
            f"trace.yml:{cursor + 1}: inside the tests: list opened at line "
            f"{index + 1}, {raw!r} is neither a list item, a comment, a blank "
            f"line nor a key closing the list -- this scan cannot tell whether "
            f"it declares a ref, which ADR-0039/R2 makes a failure rather than "
            f"a silent truncation of the list"
        )
    return tuple(refs)


def _trace_tests_refs_by_backward_scan() -> set[str]:
    """``trace.yml``'s ``tests:`` refs, read by a different algorithm entirely.

    The independent instrument for the census, and independent in the way that
    matters: it never scans *forward* from a ``tests:`` key, so no line between
    two items can terminate anything. It starts from every ``- item`` line in
    the file and walks **backwards** to the nearest key at or outside the item's
    indentation; the item belongs to a ``tests:`` list exactly when that key is
    ``tests``. A comment, a blank line or a retired-test note between two items
    is invisible to it by construction, which is precisely the blind spot of a
    forward scan.

    Falling out of that for free: an item under ``notes:``' folded prose
    resolves backwards to ``notes`` and is correctly not a ref.

    Proven, not asserted: on this file it returns exactly the same 510 refs as
    ``yaml.safe_load`` does over the parsed document, ref for ref, with an empty
    symmetric difference in both directions. PyYAML is **not** importable here
    -- it is in no part of ``pyproject.toml``, so a test that imported it would
    fail collection on a bare checkout rather than skip -- which is why the
    second reading is a second implementation instead of a parser.
    """
    lines = TRACE.read_text(encoding="utf-8").splitlines()

    def width_of(raw: str) -> int:
        return len(raw[: len(raw) - len(raw.lstrip(" \t"))].expandtabs(8))

    refs: set[str] = set()
    for index, raw in enumerate(lines):
        key = _MAPPING_KEY.match(raw)
        if key and key.group("key") == "tests":
            value = (key.group("value") or "").strip()
            if value.startswith("["):
                refs.update(_split(value.strip("[]")))
            continue
        item = _LIST_ITEM.match(raw)
        if not item:
            continue
        width = width_of(raw)
        for back in range(index - 1, -1, -1):
            owner = _MAPPING_KEY.match(lines[back])
            if owner and width_of(lines[back]) <= width:
                if owner.group("key") == "tests":
                    refs.update(_split(item.group("ref")))
                break
    return refs


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
        return "", f"requirements.yml:{index + 1} (check:)"
    ref = next((m.group("ref") for m in map(_BLOCK_REF.match, window) if m), None)
    if ref is None:
        raise RefShapeNotClassifiable(
            f"requirements.yml:{index + 1}: a block-form check of kind 'test' "
            f"declares no ref -- window {window!r}"
        )
    return ref, f"requirements.yml:{index + 1} (check:)"


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


def _digest_of(ref: str) -> str:
    """One ref's own digest. **A digest is not a ref, and that is the point.**

    Review cycle 1's round concluded that enforcing the repair-vs-signal-loss
    rule was impossible: enforcement needs the refs that LEFT a class, a stored
    ref list is exactly what G-2 forbids because it revives them, and one digest
    over a whole class cannot say who left. The first two halves are right. The
    conclusion is not, and the missing step is that the ref **population is
    re-derived at run time**: the stored artefact never has to be resolvable,
    only matchable against a set the guard rebuilds. So a *per-member* digest set
    names the departed member exactly while storing nothing a text search can
    use. ``git grep -lw 080555bfe5ee`` cannot match any ref, and the 580 digests
    on this board are collision-free -- both measured. The G-2 self-check is what
    holds the property mechanically rather than by this argument: it runs the
    whole declared set's trie over this file's own bytes.
    """
    return hashlib.sha256(ref.encode("utf-8")).hexdigest()[:12]


def _member_digests(refs: tuple[str, ...]) -> frozenset[str]:
    """A class as per-member digests -- the artefact a departure is read from."""
    return frozenset(_digest_of(ref) for ref in refs)


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
#
# Four of them were re-measured at d7eec7e7 on 2026-10-29 -- BOOKKEEPING_ONLY,
# FALSELY_ALIVE, DEFINED and SAME_FILE_PROSE -- and each carries the reading
# that moved it. One event, one cause (CARD-285's merge f13e8d85 defining three
# FR-045 cells), judged the repair direction against a def/class per ref. The
# other five did not move and were measured not to: FALSELY_DEAD, HONEST_DEAD,
# RESOLVED_FROM_AFAR, CENSUS and TRACE_TESTS, each with an EMPTY symmetric
# difference against bb7da562 rather than merely an unchanged count.
#
# --- CARD-317's method, stated ONCE -----------------------------------------
# Review cycle 1, F-005: CARD-317's first round wrote ONE union block and
# pasted it into five of these notes, so each claimed the other four's
# departures and entrants -- one note named two entrants it never gained and
# two departures that left a different class, another named nine departures it
# never had, and two classes' own figures appeared nowhere. The counts and
# digests were exact; the attribution was not, and these notes exist precisely
# so the next reader can re-derive THIS class's movement from THIS note. Fixed
# by splitting them; what is genuinely shared is the method, and it is here:
#
#   * the base is `main` at b18fd397, chosen because this module's own
#     derivation reproduces all NINE of its stored baselines there exactly --
#     that is what makes it a defensible base rather than a nearby commit;
#   * the derivation was run over the whole declared ref population at the
#     base and at HEAD and the two dumps diffed as SETS, never as counts: a
#     +1/-1 pair hides inside an unchanged total, which is exactly what two of
#     the classes below do;
#   * every entrant and every departure was then resolved against a real
#     def/class line by an INDEPENDENT `ast` index of tests/ and src/ (355
#     modules parsed, 11,016 distinct names), so the git-grep regex this module
#     uses is not both the measurement and its own witness;
#   * nothing is pasted from the failure message, which offers a ready-made
#     line and says itself that it is a prompt and not a gate.
#
# NO REF IS NAMED IN ANY OF THESE NOTES, deliberately: naming one RESOLVES it
# for the validator's text search and revives it -- this module's own G-2 cell
# caught a first draft of one of them doing exactly that. Every ref below is
# identified by its DECLARATION SITE.

#: Refs kept alive solely by pipeline bookkeeping -- the gate's class.
#: 13 at the cut (f64112f2); **15** once ``main`` was merged in, and the two that
#: arrived are this card's own mechanism firing on live data between its fix
#: rounds -- see :data:`HONEST_DEAD`.
#:
#: **2026-10-29, 15 -> 12. A REPAIR -- the first this module has seen -- and
#: recorded as such because this file's standing rule is that a departure is
#: judged repair-or-signal-loss and written down, not pasted over.** ``main``'s
#: CARD-285 merge (f13e8d85) gave real ``def``s to the three FR-045 node-id refs
#: that until then were declared by the model and defined nowhere: AC-390,
#: AC-391 and AC-392, i.e. ``tests/test_public_player_pages.py``'s
#: ``test_assembled_site_is_self_contained``,
#: ``test_pages_work_with_analytics_blocked`` and ``test_no_homegrown_tracking``
#: cells (named here as the bare test names they are; their ``path::name`` form
#: is a ref and G-2 keeps refs out of this file).
#:
#: Verified **against a ``def``/``class`` line, per ref, not with a text
#: search**: ``git grep -nE '^[[:space:]]*(def|class)[[:space:]]+<name>'`` --
#: POSIX ERE with character classes only, no ``\b``, which is undefined there
#: and silently matches nothing (:func:`_definitions`). Measured: **zero**
#: def/class lines anywhere at bb7da562 for all three, **exactly one** each at
#: d7eec7e7, each in the module its own node id names, and all three collected
#: by pytest. The merge is pinned too -- f13e8d85^1 (``main``) had none,
#: f13e8d85^2 (CARD-285's branch) had all three -- and CARD-285 added the
#: node-id rows to that module's own docstring table in the same merge, which
#: is why the same three refs entered :data:`SAME_FILE_PROSE`.
#:
#: The three were not *inferred* from a class moving by three. Membership was
#: diffed at both commits and the symmetric difference is **exactly those three
#: refs and nothing else**, on this class, on :data:`FALSELY_ALIVE`,
#: :data:`DEFINED`, :data:`SAME_FILE_PROSE` and the unpinned both-agree class,
#: and **empty** on :data:`FALSELY_DEAD`, :data:`HONEST_DEAD`,
#: :data:`RESOLVED_FROM_AFAR`, :data:`CENSUS` and :data:`TRACE_TESTS` -- which is
#: what separates a repair from a repair plus a silent regression. The departure
#: was then put to :func:`_refuse_unexplained_departures`, which recovered all
#: three by name from :data:`BOOKKEEPING_ONLY_MEMBERS`'s digests alone and judged
#: each one a repair.
# RE-DERIVED 2026-10-31 at CARD-318's merge -- measured, not pasted from the
# failure message. Each move was resolved against a real def/class line by an ast
# index of tests/ and src/ before this line changed. CARD-318's whole subject was
# registry refs that resolved only by prose, so these classes moving is the card
# working rather than drift.
#
# NO REF IS NAMED IN THESE NOTES, deliberately: naming one here RESOLVES it and so
# revives it for the validator's text search -- this module's own cell caught that
# when a first draft of this comment spelled one out. Refs are identified by site.
# One departure: the generation-path class FR-029 declares, which gained a real
# definition at tests/test_solver_strategies.py:204.
# CARD-317 (2026-10-31, fix round 1) measured this class NOT moving: 11 -> 11,
# OUT 0, IN 0, an EMPTY symmetric difference in both directions. It is the one
# class none of the card's TEN withdrawn declarations touched, because every
# one of them was resolved by a file under tests/ -- a docstring in the very
# module that covers it -- and so was never bookkeeping-only. (The gate's own
# class standing still while four others move is the reading worth keeping:
# this card drained falsely-alive and honest-dead, not this one.)
BOOKKEEPING_ONLY = (11, "2b973cfe3d340928")

#: Refs the validator reports checked while nothing defines them. A superset of
#: the above: the rest are mentioned by a comment or docstring under ``tests/``,
#: which is the limit case no pathspec can exclude.
#: 164 at the cut; **166** after the merge, the same two refs.
#:
#: **2026-10-29, 166 -> 163: the same repair and the same three refs** --
#: CARD-285's merge f13e8d85 defining AC-390/AC-391/AC-392's cells, each
#: re-derived against a ``def``/``class`` line rather than a text search, the
#: symmetric difference on this class measured to be exactly those three
#: leaving. See :data:`BOOKKEEPING_ONLY` for the per-ref verification. One
#: consistency check falls out of it and is worth keeping: all 163 remaining
#: falsely-alive refs are now ``bare``-form, because those three node ids were
#: the only non-bare members. The module docstring's pair of figures -- 191 bare
#: refs with no definition, 163 of them additionally loose-alive -- was
#: re-derived at d7eec7e7 and is unchanged by the repair, so the coincidence
#: that 163 is now *also* this whole class's size is just that.
# RE-DERIVED 2026-10-31 at CARD-318's merge -- measured, not pasted from the
# failure message. Each move was resolved against a real def/class line by an ast
# index of tests/ and src/ before this line changed. CARD-318's whole subject was
# registry refs that resolved only by prose, so these classes moving is the card
# working rather than drift.
#
# NO REF IS NAMED IN THESE NOTES, deliberately: naming one here RESOLVES it and so
# revives it for the validator's text search -- this module's own cell caught that
# when a first draft of this comment spelled one out. Refs are identified by site.
# The same single departure as BOOKKEEPING_ONLY, for the same reason.
# CARD-317 fix round 1, **162 -> 155: OUT 7, IN 0** (method above). These seven
# are this class's own, and are neither the ten the census lost nor the two that
# left HONEST_DEAD:
#   OUT  FR-019's five acceptance criteria -- requirements.yml:1098, :1104,
#        :1111, :1118 and :1125 at the base, plus trace.yml:993. Five
#        class-style declarations withdrawn; the ast index finds ZERO def/class
#        lines for any of them. They were the live 10..30 bound requirement's
#        entire ref set and they raised no warning of ANY kind, because each
#        resolved through the docstring of the very test that covers it.
#   OUT  the phantom declared TWICE -- FR-019's EC-005 (requirements.yml:1136)
#        and CON-011's `check:` (requirements.yml:6366), plus trace.yml:993 and
#        trace.yml:1226. Two declaration sites, ONE name, so ONE departure
#        here. Zero def/class lines, and it carried pytest's never-collected
#        `PropertyTest_` prefix besides.
#   OUT  ADR-0006/R1's old `check:` ref (adr/0006-dependency-baseline.md:170 at
#        the base) -- zero def/class lines, and 112 text resolvers, which is
#        what kept it in this class rather than in HONEST_DEAD.
#   IN   nothing. Every ref the card declared instead already had a real def,
#        so each entered DEFINED and none of them could enter here.
# NOT from this class: FR-042/AC-268's and AC-269's old refs. They resolved
# from nothing at all, so they were honestly dead and left HONEST_DEAD -- the
# distinction the pasted union block erased.
FALSELY_ALIVE = (155, "8465e851f42f9867")

#: Refs the validator reports DEAD while a definition exists -- the other
#: direction, not folded into the first (EC).
FALSELY_DEAD = (13, "2943a2e06c8d35ff")

#: Refs both resolvers agree are absent: an honest gap, and the only class that
#: reads correctly today -- so a ref LEAVING this class is a validator warning
#: disappearing, which is the card's headline event.
#:
#: **30 at the cut, 28 after ``main`` was merged in, and the two that left are
#: signal loss rather than repair -- re-derived against a def/class, not
#: pasted.** Both are FR-045 node-id refs under
#: ``tests/test_public_player_pages.py``. Measured with ``git grep`` against the
#: cut itself: at f64112f2 each had **zero** loose resolvers and zero
#: definitions (honest-dead, and the validator warned about both). On ``main``
#: each has **exactly one** resolver -- ``meta/review/20261029T130000Z-CARD-285-cycle1.yml``,
#: a synced cycle-1 review report -- and still **no** ``def`` or ``class``
#: anywhere. Nothing was written, nothing was repaired, and the validator's
#: warning count fell from 102 to 100 for exactly those two. That is the
#: mechanism this module exists to detect, detecting itself, unprompted; and it
#: is the departure :data:`HONEST_DEAD_MEMBERS` now makes mechanical instead of
#: leaving to a reader who has only a digest and a paste-ready line.
# RE-DERIVED 2026-10-31 at CARD-318's merge -- measured, not pasted from the
# failure message. Each move was resolved against a real def/class line by an ast
# index of tests/ and src/ before this line changed. CARD-318's whole subject was
# registry refs that resolved only by prose, so these classes moving is the card
# working rather than drift.
#
# NO REF IS NAMED IN THESE NOTES, deliberately: naming one here RESOLVES it and so
# revives it for the validator's text search -- this module's own cell caught that
# when a first draft of this comment spelled one out. Refs are identified by site.
# -10, and both reasons are repairs: seven gained real definitions in
# tests/test_solver_strategies.py, and three left because their DECLARATION was
# retired or re-pointed, so there is no longer a ref there to be dead.
# CARD-317 fix round 1, **18 -> 16: OUT 2, IN 0** (method above). Two, and they
# are the only honestly dead refs in the whole of this card's set:
#   OUT  FR-042/AC-268's and AC-269's old `test:` refs -- requirements.yml:4109
#        and :4118 at the base, plus trace.yml:2140. Zero def/class lines AND
#        zero loose resolvers each, so each raised a dead-ref WARN. Those two
#        warnings are the entirety of the card's measured 90 -> 88.
#   IN   nothing.
# NOT from this class: the other eight declarations the card withdrew. Seven
# were falsely ALIVE (see FALSELY_ALIVE) and one was a node id resolved from
# afar (see RESOLVED_FROM_AFAR) -- none of them was ever here.
# FR-001's four refs are deliberately NOT re-pointed and stay in this class;
# they are four of the 16, and FR-001's block comment in requirements.yml says
# why re-pointing them would falsify a retired criterion rather than repair it.
#
# CARD-316, **16 -> 9: OUT 7, IN 0** — the same seven :data:`CENSUS` lost, the
# same method, re-derived as a set difference rather than pasted. They were this
# class's whole requirements.yml-declared remainder apart from FR-001's four:
# before the change this class held FR-001's four (still here, still deliberate),
# the seven CARD-316 withdrew, and five declared by trace.yml alone, which this
# card does not touch. 4 + 5 = 9 is the class today, and it is derived from the
# sets rather than from the subtraction.
#
# A ref leaving here is normally a validator warning disappearing. These seven
# are the case where it is NOT: dropping an AC's `test:` trades the dead-ref
# warning for "acceptance criterion has no 'test'", one for one, on the same
# criterion — measured on the validator of record, WARN sets diffed with
# `comm`: 88 -> 88, seven out, seven in, nothing else moved. The repair is in
# what the model CLAIMS, not in the count: a criterion with no `test:` reads as
# an unverified example to forge:status and to the kanban AC/EC gate, where one
# naming a test nobody wrote read as mechanically checked.
#
# :data:`HONEST_DEAD_MEMBERS` is deliberately NOT trimmed, per its own note: all
# seven departures are WITHDRAWALS, so nothing in today's population hashes to
# their digests and :func:`_refuse_unexplained_departures` reports them as the
# documented honest residual — a count, as a `UserWarning`, with this cell's own
# exact pin as the gate. Verified: the helper's `losses` assertion stays empty
# because not one of the seven still reads alive to the validator.
HONEST_DEAD = (9, "e109f654427454a9")

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
#
# CARD-317 fix round 1, **4 -> 3: OUT 1, IN 0** (method above) -- the shrink the
# note above asked to have read, and the first time this class has moved.
#   OUT  the node-id spelling of the dependency-baseline test. At the base only
#        ADR-0042/R4 (adr/0042-book-interior-is-vector-cover-stays-raster.md:650)
#        declared it; CARD-317's fix round 0 re-pointed ADR-0006/R1's dead
#        `check:` at the SAME node id, which is how the card's one commissioned
#        repair landed inside the very class it was draining -- review cycle 1,
#        F-001. Fix round 1 deleted the 26-character path prefix from both, so
#        the string is declared nowhere and the two rules carry the bare name,
#        which resolves at its own `def` (tests/test_export_pdf.py:1249) in
#        this module and in the validator alike. Measured under the validator's
#        own pathspec: the node id resolved from 58 tracked files, not one of
#        them the module holding that `def`; the bare name resolves from 82,
#        that module included.
#   IN   nothing. A bare name cannot enter: this class selects node-id refs.
#        The three that remain are `tests/test_player_bundle.py`'s and are this
#        board's standing debt, unchanged.
# The sharp half below still measures TWO review-only members, re-derived: the
# departed ref was never one of them (it also had meta/profiling and
# meta/kanban resolvers), so that figure is independent of this move.
RESOLVED_FROM_AFAR = (3, "643e468dc7f7d76f")

#: The whole census: every verifying ref the four authorities declare. Pinned
#: because this module and ADR-0039 both STATE this number, and a stated figure
#: that nothing checks is the exact defect this card is about -- ADR-0006/R1's
#: ref read as mechanically checked for months on a pointer nobody re-derived.
#: Derived at HEAD, every term re-measured rather than carried:
#:
#: * ``trace.yml``'s ``tests:`` lists (block and inline): **510**;
#: * ``requirements.yml``: **404** -- 401 distinct from its 421 ``test:`` keys
#:   and 10 from its 11 block-form ``check:`` blocks (the eleventh is not of
#:   kind ``test``), with **7** refs declared by both, so 401 + 10 is 411
#:   *mentions* and 404 distinct. An earlier figure of "401 + 10 = 404" was
#:   quoted without the overlap and does not add up on its face; the overlap is
#:   what reconciles it;
#: * the ADRs' inline ``check: {kind: test}``: **44** distinct, from **45**
#:   occurrences and **47** ref-mentions (one occurrence declares two
#:   comma-separated refs; one ref is declared three times and one twice).
#:
#: Unioned, so a ref declared by two authorities is one entry: **580**. At the
#: cut (f64112f2) the same derivation gave **579**, with 44 ADR occurrences and
#: 43 distinct; ``main`` then declared one new ref
#: (``requirements.yml``/``trace.yml`` + one more ADR occurrence), and that ref
#: has a real definition -- which is why :data:`DEFINED` moved by one too. The
#: three figures that were wrong are kept straight in ADR-0039's table, and the
#: coincidence worth naming is that 580 was once an *erroneous* census (ADR
#: occurrences counted as refs at the cut) and is now the correct one.
#:
#: **2026-10-30, 580 -> 583** (CARD-304 fix round 1, when ``main`` was merged
#: into ``card/304``). CARD-304 flips ADR-0039/R4 from ``{kind: review-lens}``
#: to ``{kind: test}`` with three comma-separated refs, so the ADRs'
#: contribution becomes 47 distinct from 48 occurrences and 50 ref-mentions,
#: and the union gains three. Re-derived as the symmetric difference of the
#: whole census against ``main`` (0ea64cf3): exactly three refs enter and
#: nothing leaves, which is the direction a flip to ``{kind: test}`` must
#: move it. The refs are NOT named here -- G-2: this file would resolve them
#: -- and they do not need to be: all three are defined, so
#: :data:`DEFINED` moves by the same three, at
#: ``tests/test_suite_profile.py:6076``, ``:6371`` and ``:6403``, each read
#: off a ``def`` line rather than searched for.
#:
#: **2026-10-30, 583 -> 586** (CARD-314 fix round 3, when ``main`` was merged
#: into ``card/314``). One authority moves: ``trace.yml``'s CON-020 row gains
#: three entries in its ``tests:`` list, so ``trace.yml``'s contribution
#: becomes 513 (:data:`TRACE_TESTS`) and the union gains three. Neither
#: ``requirements.yml`` (404) nor the ADRs (47 distinct) changed -- all three
#: refs are declared by ``trace.yml`` alone, so there is no new overlap to
#: reconcile and 586 is 583 + 3 with no term cancelling. Re-derived as the
#: symmetric difference of the WHOLE census against the base: exactly three
#: refs enter and **nothing leaves**. The base is ``2c9238bc``, this merge's
#: second parent -- ``main``'s tip as it was merged in -- and it reproduces all
#: three stored baselines (583, 510, 392) exactly, which is what makes it the
#: defensible base rather than merely a nearby commit. Unnamed here (G-2); all
#: three are defined, so :data:`DEFINED` moves by the same three.
# RE-DERIVED 2026-10-31 at CARD-318's merge -- measured, not pasted from the
# failure message. Each move was resolved against a real def/class line by an ast
# index of tests/ and src/ before this line changed. CARD-318's whole subject was
# registry refs that resolved only by prose, so these classes moving is the card
# working rather than drift.
#
# NO REF IS NAMED IN THESE NOTES, deliberately: naming one here RESOLVES it and so
# revives it for the validator's text search -- this module's own cell caught that
# when a first draft of this comment spelled one out. Refs are identified by site.
# Count unchanged at 586, digest moved: the same three retired declarations out
# and their three defined replacements in.
# CARD-317 fix round 1, **586 -> 580: OUT 10, IN 4** (method above). This is
# the union over all four authorities, so it is the one class whose figures
# count every withdrawn and every added DECLARATION exactly once -- which is
# also why its OUT differs from every other class's:
#   OUT  the nine class-style names with zero def/class lines anywhere:
#        FR-019's five criteria (requirements.yml:1098..:1125), the phantom its
#        EC-005 and CON-011's `check:` share (requirements.yml:1136 and :6366 --
#        two sites, ONE name, ONE departure), FR-042/AC-268's and AC-269's old
#        refs (requirements.yml:4109, :4118), and ADR-0006/R1's old `check:`
#        (adr/0006-dependency-baseline.md:170 at the base; 112 text resolvers).
#   OUT  one more that fix round 1 added, and it is a FORM change rather than a
#        loss: the node-id spelling of the dependency-baseline test. At the base
#        ADR-0042/R4 (adr/0042-book-interior-is-vector-cover-stays-raster.md:650)
#        declared it alone; fix round 0 made ADR-0006/R1 declare the same
#        string; fix round 1 deleted the 26-character path prefix from BOTH, so
#        no authority declares that spelling any more. Its definition never
#        moved.
#   IN   four, each with a real def line: the BARE name the two ADR rules now
#        carry (adr/0006-...:170, adr/0042-...:650); FR-042/AC-268's new ref
#        (requirements.yml:4182, trace.yml:2155); and AC-269's TWO new refs,
#        comma-separated at requirements.yml:4219 -- the wiring test, also at
#        trace.yml:2155, and fix round 1's caption read-back, which
#        requirements.yml alone declares.
# 586 - 10 + 4 = 580. The count alone would have read 586 -> 580 whichever refs
# moved, which is the whole reason the SETS were diffed.
#
# CARD-316, **580 -> 573: OUT 7, IN 0** — re-derived as the symmetric difference
# of the whole census before and after the change (scratchpad/card316/
# census_snapshot.py, which reproduced all nine stored baselines, count AND
# digest, on the unchanged tree before anything was edited). NOT pasted from the
# failure message this cell offers.
#   OUT  the seven `test:` keys CARD-316 WITHDREW from requirements.yml,
#        identified by site and not by name (G-2): FR-028/AC-129's and AC-134's,
#        FR-032/AC-191's and AC-192's, FR-035/AC-206's and AC-207's, and
#        FR-040/AC-379's. Each named a test nobody is to write — four state a
#        DEC branch the project rejected (DEC-034/ADR-0027,
#        DEC-036/ADR-0034), two a feature the model retired as unimplemented,
#        one a test CARD-226 still owes.
#   IN   nothing. No declaration was added.
# This is a WITHDRAWAL, which is the distinction the note above insists on: the
# seven did not stop being resolved, they stopped being DECLARED. All seven had
# zero `def`/`class` lines anywhere under src/ or tests/ before the change (an
# `ast` index of 11005 symbols, read off definition nodes, not a text search),
# so none of them could have been a repair-by-definition and none was lost to
# erosion either. Each was declared by requirements.yml ALONE — zero mentions in
# trace.yml and zero in the ADRs — which is why the census loses exactly seven
# and the overlap terms above do not change. :data:`TRACE_TESTS` (507) and
# :data:`DEFINED` (409) stood still, measured, both directions empty.
CENSUS = (573, "2e0233d69e413369")

#: ``trace.yml``'s contribution on its own, pinned separately because it is the
#: authority whose scan was broken: a ``break`` on a ``#`` comment inside a
#: ``tests:`` list derived 494 of these 510 and raised nothing.
#:
#: **2026-10-30, 510 -> 513** (CARD-314 fix round 3, after ``main`` was merged
#: into ``card/314``). The card re-stamped ``trace.yml``'s CON-020 row with
#: three more entries in its ``tests:`` list, so this authority -- and only
#: this one -- gains three; :data:`CENSUS` and :data:`DEFINED` move by the same
#: three, which is what one declaration event arriving with its definitions
#: already in place looks like across all three classes. Re-derived as the
#: symmetric difference of this class against the base, using this module's own
#: :func:`_declared_refs`: exactly three refs enter and **nothing leaves**.
#: Unnamed here (G-2); see :data:`DEFINED` for where each one is defined.
# RE-DERIVED 2026-10-31 at CARD-318's merge -- measured, not pasted from the
# failure message. Each move was resolved against a real def/class line by an ast
# index of tests/ and src/ before this line changed. CARD-318's whole subject was
# registry refs that resolved only by prose, so these classes moving is the card
# working rather than drift.
#
# NO REF IS NAMED IN THESE NOTES, deliberately: naming one here RESOLVES it and so
# revives it for the validator's text search -- this module's own cell caught that
# when a first draft of this comment spelled one out. Refs are identified by site.
# Count unchanged at 513, digest moved: three out, three in. The three departures
# are defined nowhere (two retired property spellings and AC-142's retired
# target); all three entrants have a definition line.
# CARD-317 fix round 1, **513 -> 507: OUT 8, IN 2** (method above). Eight and
# not the census's ten, and the two reasons are both structural rather than
# arithmetic: `trace.yml` names a ref once per ROW, and it declares neither ADR
# rule's check:
#   OUT  six from FR-019's row (trace.yml:993) -- its five criteria refs and
#        the shared phantom. The phantom is withdrawn from CON-011's row
#        (trace.yml:1226) as well, so SEVEN declaration sites leave but SIX
#        names do, and a name is what this class counts.
#   OUT  FR-042/AC-268's and AC-269's old refs, from trace.yml:2140.
#   IN   two, both at trace.yml:2155 and both defined: AC-268's new ref
#        (tests/test_book_pdf_band.py:1483) and AC-269's wiring ref
#        (tests/test_book_solved_answer_key.py:308).
# 513 - 8 + 2 = 507. Three refs that move CENSUS do not appear here at all:
# the two ADR-rule spellings of the dependency-baseline test, which `trace.yml`
# never declared, and AC-269's fix-round-1 caption read-back, which
# requirements.yml declares alone.
TRACE_TESTS = (507, "06021d84f972abd1")

#: Every ref that resolves to a real ``def``/``class``. AC-3's first half used
#: to assert ``> 300`` against a measured 382 -- 82 refs of headroom, i.e. the
#: claim "honest refs are not absorbed" could have gone on passing while a
#: quarter of them stopped being honest. Pinned exact like every other class
#: here. **This is the one count the F-001 repair moved**: 382 -> 385, which is
#: exactly the 3 refs the silent drop had removed from the census, each of them
#: a real ``class`` in ``tests/test_book_puzzle_frame.py``. It then moved again,
#: 385 -> 386, when ``main`` was merged in: one new ref declared there, defined
#: at ``tests/test_book_pdf.py:1797``. Re-derived against that ``def``, so the
#: move is recorded as the honest event it is rather than as a digest update.
#:
#: **2026-10-29, 386 -> 389**: the same three refs arriving from the other side.
#: CARD-285's merge (f13e8d85) defined AC-390/AC-391/AC-392's cells in
#: ``tests/test_public_player_pages.py`` at lines 2587, 2768 and 2884, each
#: confirmed by a ``def`` line read off that commit -- not by a text search, and
#: not by trusting that a class moving by three moved by *these* three: the
#: symmetric difference against bb7da562 is exactly those three entering and
#: nothing leaving. They are the same three that left :data:`BOOKKEEPING_ONLY`
#: and :data:`FALSELY_ALIVE`, so this is the repair direction of one event and
#: not three independent moves.
#:
#: **2026-10-30, 389 -> 392**: ADR-0039/R4's flip to ``{kind: test}``, the
#: same event that moved :data:`CENSUS` by three. The symmetric difference
#: against ``main`` (0ea64cf3) is exactly three entering and nothing leaving,
#: and each one's ``def`` line was read in ``tests/test_suite_profile.py`` at
#: 6076, 6371 and 6403 -- so the move is a DECLARATION arriving with its
#: definition already in place, which is the one direction of census movement
#: that needs no repair. Unnamed here for the same G-2 reason as above.
#:
#: **2026-10-30, 392 -> 395**: CARD-314's CON-020 re-stamp, the same event that
#: moved :data:`CENSUS` and :data:`TRACE_TESTS` by three. The symmetric
#: difference against the base (``2c9238bc``, named at :data:`CENSUS`) is
#: exactly three entering and **nothing leaving** -- so this is again a
#: DECLARATION arriving with its definition already in place, the one direction
#: of movement that needs no repair, and not a class shrinking because a file
#: was synced in. Each entering ref was resolved to a real ``class`` line in
#: ``tests/test_book_interior_type_floor.py`` at **1164**, **1804** and
#: **2114**, read off the line itself rather than text-searched: all three
#: match ``^class <name>[(:]`` there, as do the CON-020 row's other seven, so
#: that row's ten refs all resolve after the round's rename. Unnamed here for
#: the same G-2 reason as above.
#:
#: The derivation was proved in both directions rather than asserted. On two
#: out-of-tree mutants of this same commit: removing ONE of the three entries
#: from the ``tests:`` list gives 394 with two entering and 512 on
#: :data:`TRACE_TESTS`; renaming ONE of the three ``class`` lines (line count
#: preserved, blob checked back) gives 394 with two entering while
#: :data:`TRACE_TESTS` stays 513 -- so the two halves of the measurement are
#: independent, and a derivation that could not tell those trees apart would
#: not be one.
# RE-DERIVED 2026-10-31 at CARD-318's merge -- measured, not pasted from the
# failure message. Each move was resolved against a real def/class line by an ast
# index of tests/ and src/ before this line changed. CARD-318's whole subject was
# registry refs that resolved only by prose, so these classes moving is the card
# working rather than drift.
#
# NO REF IS NAMED IN THESE NOTES, deliberately: naming one here RESOLVES it and so
# revives it for the validator's text search -- this module's own cell caught that
# when a first draft of this comment spelled one out. Refs are identified by site.
# +11, all in CARD-318's own files: eight classes written to carry the registry's
# exact names (tests/test_solver_strategies.py), the two property classes renamed
# out of the never-collected prefix (python_classes is matched as a PREFIX, not a
# glob, so the old spelling was silently never collected -- :203 and :304 of
# tests/property/test_solve_strategies.py now are), and AC-142's re-pointed
# function at tests/test_strategies.py:490.
# CARD-317 fix round 1, **406 -> 409: OUT 1, IN 4** (method above). This is the
# class the pasted union block described worst -- it claimed nine departures
# this class never had. None of the nine class-style names the card withdrew
# was ever here: all nine had ZERO def/class lines, which is exactly why they
# sat in FALSELY_ALIVE or HONEST_DEAD instead.
#   OUT  one, and it is a FORM change and not a loss: the node-id spelling of
#        the dependency-baseline test stopped being declared when both ADR
#        rules (adr/0006-...:170, adr/0042-...:650) dropped the path prefix.
#        tests/test_export_pdf.py:1249 is untouched and still collects.
#   IN   four defs, each read off its own `def` line rather than searched for:
#        tests/test_export_pdf.py:1249 (the bare name the two ADR rules now
#        carry -- the same definition the departure above pointed at, reached by
#        an honest spelling), tests/test_book_pdf_band.py:1483 (AC-268's new
#        ref), tests/test_book_solved_answer_key.py:308 (AC-269's wiring ref)
#        and tests/test_book_pdf_band.py:1536 (AC-269's fix-round-1 caption
#        read-back, the F-003 close).
# So 406 - 1 + 4 = 409, and three of the four entrants are DECLARATIONS arriving
# with their definitions already in place -- the one direction of movement that
# needs no repair.
DEFINED = (409, "a8f3ac02034906d1")

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
#:
#: **2026-10-29, 16 -> 19: the same event, fourth class.** CARD-285's merge
#: (f13e8d85) added AC-390/AC-391/AC-392 to ``tests/test_public_player_pages.py``'s
#: own docstring node-id table *and* the three ``def``s in the same merge, so
#: the three refs acquired both halves of this class's predicate at once --
#: definition and same-file prose mention. Verified against the ``def`` lines
#: (zero at bb7da562, one each at d7eec7e7, in the named module) rather than by
#: a text search, and the symmetric difference on this class is exactly those
#: three entering. That the shim module was already one of the four listed above
#: is why nothing else here had to change.
SAME_FILE_PROSE = (19, "e899a08818a9c4be")

#: **Per-member digests of the two classes whose shrink is answerable
#: mechanically** -- the enforceable half of repair-vs-signal-loss, and the
#: thing a single class digest could only describe in English.
#:
#: Why only these two. A departure is answerable when exactly one question
#: decides whether it was a repair, and :func:`_refuse_unexplained_departures`
#: asks it: *does the departed ref carry a ``def``/``class`` now, or is it at
#: least loose-DEAD now so the validator warns about it honestly?* For
#: :data:`HONEST_DEAD` a departure is a warning vanishing, and for
#: :data:`BOOKKEEPING_ONLY` it is the gate's own class losing a member, so in
#: both cases a "no" to that question is signal loss by this card's definition.
#: For :data:`FALSELY_ALIVE`, :data:`CENSUS`, :data:`DEFINED` and
#: :data:`TRACE_TESTS` there is no single such question -- and they are 163, 580,
#: 389 and 510 members, so a per-member set for them would put thousands of hex
#: characters in this file to answer a question nobody can state.
#:
#: **What closes them -- and what does not.** An earlier version of this comment
#: said their closure is *the partition arithmetic*: that
#: ``376 + 163 + 13 + 28 = 580`` and ``389 = 13 + 376`` leave no room for a ref
#: to move unnoticed. **That argument is withdrawn: it is a tautology.** The four
#: predicates partition on ``(bool(loose), bool(strict))`` and ``defined`` is the
#: union of two of those four cells, so both identities hold BY CONSTRUCTION --
#: measured over 2000 randomly generated synthetic verdict populations, they were
#: violated **0** times. Neither sum can ever red, so neither is a control, and
#: offering a restatement as a verified closure is precisely the defect this
#: module exists to detect. Review cycle 3 found it here, which is the mechanism
#: landing on the mechanism's own prose.
#:
#: The honest argument is the digests, and it is strictly stronger. Each of the
#: four classes is pinned as an exact ``(count, SHA-256 over its sorted members)``
#: pair, so **no** membership change is silent -- a COUNT-PRESERVING swap
#: included. Measured rather than argued: moving one ref out of
#: :data:`FALSELY_ALIVE` and another in leaves the count unmoved (**166** when
#: that swap was measured, **163** today) and MOVES the digest. The identities
#: above were re-derived at d7eec7e7 after CARD-285's merge: they moved to
#: ``376 + 163 + 13 + 28`` and ``389 = 13 + 376`` and, being tautologies, held
#: without being checked -- which is exactly why they are not the argument.
#: So *detection* is closed for all four of these classes by the pins
#: alone; what is not closed is *naming* the departed member, which is the only
#: thing a per-member set buys and which needs the single mechanical question
#: these four do not have. The two sums above stay true and are worth reading as
#: a consistency check on a human's own re-derivation. They are not a mechanism,
#: and nothing here would fail if they were deleted.
#:
#: G-2: a 12-hex digest is not a ref and resolves nothing -- asserted, not
#: argued, by :func:`test_this_module_resolves_no_verifying_ref_at_all` running
#: the whole declared set's trie over this file's bytes.
#: **2026-10-29, 15 -> 12 digests.** Three members left on CARD-285's merge and
#: :func:`_refuse_unexplained_departures` met its first real **repair**: given
#: the stored 15 and the derived 12 it recovered ``67727cff20af``,
#: ``cc7262aedc8f`` and ``efad4f46f347`` by re-hashing the whole 580-ref
#: population, named all three, found a ``def`` for each
#: (``tests/test_public_player_pages.py`` lines 2884, 2768 and 2587), judged
#: each a repair, returned without raising and issued **no** withdrawal warning
#: -- the correct output, and the first evidence that the helper's green
#: direction is reachable rather than only its red one. Both directions were
#: proved on this same unmutated tree before the set was touched: dropping one
#: surviving member instead reds with ``left WITHOUT gaining a def/class ...
#: That is SIGNAL LOSS``, naming the ref, and a digest matching no declared ref
#: still warns about a withdrawal. The 12 below are the stored 15 minus those
#: three, checked as a set identity and not retyped.
BOOKKEEPING_ONLY_MEMBERS = frozenset(
    {
        "080555bfe5ee", "1eb591d49a25", "29e08f59dc97", "5dffd6a19d09",
        "65011680c167", "6971a52601f1", "70e3102a3463", "80168d60bd5b",
        "be5117c9525f", "c19c9922ca0a", "cae6c630eb4b", "fd377ad19c33",
    }
)

#: **A stored SNAPSHOT of :data:`HONEST_DEAD`'s membership, not the class.** The
#: 28 digests below were measured when the set was written; the class is
#: :data:`HONEST_DEAD` members today and is smaller, and the gap is the point of
#: the set rather than a staleness in it -- :func:`_refuse_unexplained_departures`
#: recovers a departed ref by re-hashing the whole re-derived population against
#: these digests, which only works for departures that are still IN the snapshot
#: and no longer in the class. (This sentence used to open "The 28 members of
#: HONEST_DEAD", which read as a count of the class and was wrong by 10 by the
#: time CARD-317 measured it -- already wrong by 2 on main. The snapshot is
#: deliberately NOT trimmed to the class: erasing a digest makes that retirement
#: unrecoverable by name, and the ``UserWarning`` the helper raises for a digest
#: matching nothing declared today is the documented honest-residual path.)
#:
#: The two that left when ``main`` was merged in were re-derived against a
#: ``def``/``class``, found to have none, and recorded on :data:`HONEST_DEAD` as
#: signal loss. Had this set existed one merge earlier,
#: :func:`_refuse_unexplained_departures` would have named both by itself --
#: which is the measurement behind taking review cycle 2's counter-example
#: rather than restating the refusal.
HONEST_DEAD_MEMBERS = frozenset(
    {
        "036d0ebf4aa2", "0df83fbf2e09", "10c62d9a9310", "18b227c7c63e",
        "35147234566c", "37410c6d83f1", "3af12f7aad47", "3d0816e8981f",
        "3dc2d668529d", "4fd2f3f82707", "5989c001ec2a", "64cb91389bdd",
        "706b6f89e198", "724703d80fe5", "751ab66ab856", "779d88646ffd",
        "7d23efdda011", "7fe155ce4ee7", "9701bc0b3f85", "9c951b39bf87",
        "9de898a558be", "a8cd42d7bc1e", "bdaa2b084e1b", "c2a2ccef71ff",
        "d2b90c440d41", "de54ba7800a7", "eb8e625174c7", "fb5e99ae0ae7",
    }
)


def _refuse_unexplained_departures(
    label: str, stored: frozenset[str], members: tuple[Verdict, ...]
) -> None:
    """A ref that LEFT this class must have left for a reason that is not erosion.

    The enforceable form of *"a class that shrinks because a review report was
    synced in is signal loss, not a fix"*. The departed member is named without
    any name being stored: the missing per-member digest is matched against the
    digest of every ref the model declares **today**, re-derived, and the one it
    matches is the departed ref. Then the mechanical question is asked --
    ``_strict_resolution`` for a definition, ``_loose_resolution`` for whether
    the validator at least warns honestly now -- and a departure that answers
    "no" to both reds here, by name, with its remaining resolvers printed.

    The one honest residual, and it is distinguishable rather than hidden: if the
    departed ref's **declaration** also left the model, nothing in today's
    population hashes to the missing digest and it cannot be named. That case
    moves :data:`CENSUS`, which is pinned exactly, so it reds there instead, and
    it is reported here as a count -- **unconditionally**, as a warning, so the
    two cases are never confused even when withdrawal is the ONLY departure.

    That last word is review cycle 3's F-004c3, and the earlier version of this
    sentence was measured FALSE in exactly the case it is about: the count was
    interpolated into the assertion message below, the assertion only renders
    when ``losses`` is non-empty, so a **pure** withdrawal returned from here in
    total silence while this docstring claimed it was reported. The module's own
    case-4 control asserted only that it did not raise, so the claim had no
    control that could fail in its own direction -- which is ADR-0039/R1's whole
    subject, landing on this card's code for the third cycle running. The
    warning is now the report and
    :func:`test_a_departed_member_is_recovered_by_name_and_its_departure_judged`
    case 4 asserts it is issued and names the count.
    """
    departed = stored - _member_digests(tuple(verdict.ref for verdict in members))
    if not departed:
        return
    population = {_digest_of(declared.ref): declared for declared in _declared_refs()}
    recovered = [population[digest] for digest in sorted(departed) if digest in population]
    withdrawn = len(departed) - len(recovered)
    if withdrawn:
        warnings.warn(
            f"the {label!r} class lost {withdrawn} member(s) whose digest matches "
            f"no ref the model declares today: the DECLARATION left and not just "
            f"the class membership, so this helper cannot name the ref and does "
            f"not claim to have judged it. That case moves CENSUS, which is "
            f"pinned exactly, so it reds there -- re-derive the census against a "
            f"def/class rather than updating a baseline. Reported here "
            f"unconditionally because the assertion below renders only when some "
            f"OTHER member also departed, and a pure withdrawal used to return "
            f"from here silently (F-004c3).",
            stacklevel=2,
        )
    losses = {
        declared.ref: _loose_resolution().get(declared.ref, ())
        for declared in recovered
        if not _strict_resolution(declared) and _loose_resolution().get(declared.ref)
    }
    assert not losses, (
        f"the {label!r} class lost {len(departed)} member(s), and {len(losses)} of "
        f"them left WITHOUT gaining a def/class and while still reading as alive "
        f"to the validator. That is SIGNAL LOSS, not a repair:\n"
        + "\n".join(
            f"  {ref}\n      still resolved by : {', '.join(hits)}\n"
            f"      defined at        : (nowhere)"
            for ref, hits in sorted(losses.items())
        )
        + (
            f"\n(plus {withdrawn} digest(s) matching no ref the model declares "
            f"today -- the declaration itself left, which moves CENSUS and reds "
            f"there.)"
            if withdrawn
            else ""
        )
        + f"\nThe departed refs above were named by re-deriving the whole "
        f"{len(population)}-ref population and matching the missing per-member "
        f"digests; no ref is stored anywhere in this module (G-2). If a "
        f"departure really is a repair, the ref carries a def/class and this "
        f"cell goes green without anything being pasted."
    )



def _class_of(predicate) -> tuple[Verdict, ...]:
    return tuple(verdict for verdict in _verdicts() if predicate(verdict))


def _assert_class(
    label: str,
    baseline: tuple[int, str],
    members: tuple[Verdict, ...],
    stored_members: frozenset[str] | None = None,
) -> None:
    """Hold one derived class to its measured count and digest.

    **The shrink direction, and the claim here that review cycle 2 refuted.**
    This docstring used to say: enforcing *"a class that shrinks because a review
    report was synced in is signal loss, not a fix"* would need a stored ref
    list, G-2 forbids one, a digest cannot say who left, and therefore "the
    property that makes the guard safe is the property that makes the response
    unenforceable". **That last sentence is false as written, and it was the
    sharpest claim in the round that wrote it** -- which is this card's own
    subject, so it is corrected here rather than quietly dropped.

    It is true of ONE digest over a whole class, which cannot name a member. It
    does not follow that no artefact can, because the ref population is
    **re-derived at run time**: a stored *per-member* digest set never has to be
    resolvable, only matchable against a set the guard rebuilds. See
    :func:`_digest_of` and :func:`_refuse_unexplained_departures`, which is now
    wired into the two classes whose shrink reduces to one mechanical question
    (:data:`BOOKKEEPING_ONLY_MEMBERS`, :data:`HONEST_DEAD_MEMBERS`) and which
    names the departed ref and asserts the departure was a repair.

    What stays a prompt rather than a gate is narrower, and stated as such: for a
    class with no per-member set -- :data:`FALSELY_ALIVE`, :data:`CENSUS`,
    :data:`DEFINED`, :data:`TRACE_TESTS` -- the message below is still a message,
    and the paste-ready line is offered knowing it is also the lazy exit. The
    gate is that the cell reds at all, in either direction.

    The one thing that IS mechanical: whatever the class moved to must still
    satisfy every other cell here, so a baseline updated without re-derivation
    typically moves the partition, the census or the gate as well.
    """
    if stored_members is not None:
        # Before the count, because "two members left and here they are" is a
        # better failure than "the digest changed".
        _refuse_unexplained_departures(label, stored_members, members)
    refs = tuple(verdict.ref for verdict in members)
    actual = (len(refs), _fingerprint(refs))
    assert actual == baseline, (
        f"the {label!r} class moved: measured {actual}, baseline {baseline}.\n"
        f"This is not automatically a regression and not automatically a repair "
        f"-- re-derive each ref against a def/class before updating the baseline, "
        f"because a class that shrinks because a review report was synced in is "
        f"signal loss, not a fix. Nothing below checks that you did: the "
        f"baseline is a digest and not a ref list (G-2), so this message is a "
        f"prompt and not a gate -- see _assert_class's docstring for why that "
        f"trade is deliberate.\nOnce re-derived, the line to paste is\n"
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
    _assert_class("bookkeeping-only", BOOKKEEPING_ONLY, members, BOOKKEEPING_ONLY_MEMBERS)


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
        HONEST_DEAD_MEMBERS,
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
    # The sharp half: for some of them NOTHING but review YAMLs resolves the
    # ref. That is the case a reader will not believe without it being
    # asserted, and it is the one CARD-307 exists for.
    #
    # The figure is TWO, and it is worth saying why it is not three. This
    # module's first draft asserted three, on the reading that all three of
    # ``tests/test_player_bundle.py``'s refs were review-only. The assertion
    # red: the third is ALSO named by ``tests/test_public_player.py``'s own
    # docstring node-id table, so a second module's shim is carrying it. The
    # overstatement was mine and the control caught it, which is the whole
    # argument of ADR-0039/R1 arriving on this card's own work.
    review_only = [
        verdict.ref
        for verdict in members
        if verdict.loose and all(hit.startswith("meta/review/") for hit in verdict.loose)
    ]
    assert len(review_only) == 2, (
        f"expected exactly two node-id refs resolved by review reports alone; "
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
#
# Both pins below are PERMANENT instances -- refs whose test never landed -- and
# that is a limit of pinning, stated rather than papered over. The card's second
# measured instance was TRANSIENT: CARD-291's ref was revived by its own review
# sync and then became a real `def` when the card merged, so a test naming it
# would have been green for one reading and red for the next through no change
# of its own. A transient instance cannot be pinned stably BY CONSTRUCTION: the
# thing that makes it transient is that it stops being a member. What covers it
# is the generic half -- the gate's class is pinned as a count and a digest, so a
# transient member ARRIVING reds the gate on the way in and LEAVING reds it again
# on the way out, and both have to be read against a def/class. The named pins
# are for the permanent case precisely because that is the case a count alone
# would let sit still forever.

#: NFR-001/AC-038's ref -- the permanent case. Its warning was retired by the
#: CARD-301 cycle-1 review report alone, and the test it names has never
#: existed. Confirmed at f64112f2: no ``def`` and no ``class`` anywhere, and
#: exactly two resolvers, one of them ``meta/kanban/dispatcher.state`` -- which
#: the orchestrator wrote while recording this defect. Re-derived at HEAD after
#: ``main`` was merged in: still no definition, still exactly those two
#: resolvers.
_AC038_REF = "TestGenerate_50x50_" + "RespectsTimeoutBound"

#: A node-id instance of the same class -- **and now the board's record of one
#: that has been repaired.** AC-4 as drafted named
#: ``tests/test_approval_guess_gate.py::test_unknown_verdict_…closed``
#: (CARD-291's); that ref was repaired, so the cell was re-pointed at
#: FR-045/AC-392's, which was then resolved by three CARD-218/CARD-284 review
#: reports and nothing else. **CARD-285's merge (f13e8d85) repaired that one
#: too**, which is how this pin came to red on 2026-10-29: the cell was pinning
#: a live defect, so it died with its own subject -- the second repair in a row
#: to kill it. Re-pointing at a surviving member would re-arm the same trap
#: against the next repair, and makes a detector's fixture out of the board's
#: current defect list, which is the wrong incentive: the cell would then reward
#: the board for staying broken.
#:
#: So the detection half no longer rests on this ref at all. It is built
#: synthetically in
#: :func:`test_the_node_id_eroded_instance_is_detected`, and this ref stays
#: pinned only in the direction that **cannot** destroy itself: a repair staying
#: repaired. Re-erosion -- the ``def`` deleted or renamed while the model goes on
#: declaring the node id -- reds that cell, and a repair never un-repairs itself
#: by a review YAML being synced in, which is the asymmetry the old design
#: lacked.
_AC392_REF = "tests/test_public_player_pages.py" + "::" + "test_no_homegrown_tracking"

#: The synthetic eroded ref: a node id in a module that does not exist, declared
#: by a synthetic authority set and resolved by a synthetic review YAML. It is
#: deliberately not any ref the model declares -- see
#: :func:`test_the_node_id_eroded_instance_is_detected` for why the detector's
#: fixture must not be a live defect.
_SYNTHETIC_ERODED = (
    "tests/test_synthetic_card308_authority.py" + "::" + "test_synthetic_eroded_node_id"
)

#: Its control: the same shape with a definition in the module it names, which
#: the detector must NOT report. Without it the cell passes on a detector that
#: reports every node-id ref it is shown.
_SYNTHETIC_DEFINED = (
    "tests/test_synthetic_card308_authority.py" + "::" + "test_synthetic_defined_node_id"
)


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


def test_the_node_id_eroded_instance_is_detected(tmp_path, monkeypatch) -> None:
    """AC-4, second half: the same class reached through a node-id ref.

    A detector that only catches the bare-name case would read as working while
    the node-id case erodes every wave, and the node-id form is the one the
    board is migrating to (CARD-294, CARD-291, CARD-307).

    **Why this is synthetic, and the measurement that forced it.** This cell
    used to pin a *live* member of the gate's class by name, and it has now been
    killed twice by the thing it is supposed to encourage: CARD-291's merge
    repaired the ref AC-4 was drafted against, and CARD-285's merge (f13e8d85)
    repaired its replacement, :data:`_AC392_REF`, taking this cell red with it
    at d7eec7e7. A detector test whose fixture is the board's current defect
    list cannot survive the defects being fixed. Worse, it inverts the
    incentive: the cheap way to green is for the board to keep an eroded ref
    around, and the third re-pointing would simply re-arm the trap for the next
    repair.

    So the eroded shape is **constructed** here, against a synthetic authority
    set in ``tmp_path`` and a synthetic resolution over files that exist only in
    memory -- the same technique as
    :func:`test_an_unreadable_declaration_key_shape_is_a_failure_and_not_a_skip`'s
    26-shape matrix, and no tracked file is written at any point. What the cell
    proves is therefore about the detector and not about the board: a node-id
    ref that the loose search resolves only from ``meta/review/``, with no
    ``def`` in the module it names, **is** reported by
    :attr:`Verdict.bookkeeping_only`, and the same shape with a real definition
    is **not**.

    What is faked and what is not, stated so the cell is not read as more than
    it is. Real: the authority derivation (:func:`_declared_refs` over the
    synthetic YAML), :attr:`Declared.form`, :func:`_trie_pattern` (so the loose
    hits are found with ``git grep -lw``'s own word boundaries rather than by
    ``in``), :func:`_strict_resolution`, every :class:`Verdict` predicate and
    :func:`_class_of`. Faked: the two file searches' *domain* -- which files
    exist and what they contain. Their fidelity to the validator is a separate
    claim with its own controls
    (:func:`test_the_loose_resolver_agrees_with_git_grep_itself` and
    :func:`test_the_definition_search_finds_a_definition_known_to_exist`), and
    the live board's membership is pinned by :data:`BOOKKEEPING_ONLY`, so
    nothing is left uncovered by moving this cell off a live instance.

    The edge mutant for this cell is anything that stops the detector
    detecting: ``bookkeeping_only`` returning ``False``, ``falsely_alive``
    dropping its ``not self.strict`` term, or ``meta/review/`` being added to
    :data:`CODE_ROOTS`. Measured out of tree on a copy of this module: each
    reds this cell by name.
    """
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    requirements = tmp_path / "requirements.yml"
    trace = tmp_path / "trace.yml"
    (adr_dir / "0001-synthetic.md").write_text(
        "# Synthetic ADR\n\n```yaml\n- id: SYN/R1\n"
        f"  check: {{kind: test, ref: {_SYNTHETIC_ERODED}}}\n```\n",
        encoding="utf-8",
    )
    requirements.write_text(
        f"requirements:\n  - id: SYN-001\n    test: {_SYNTHETIC_DEFINED}\n",
        encoding="utf-8",
    )
    trace.write_text(
        f"covered:\n  - id: SYN-001\n    tests:\n      - {_SYNTHETIC_ERODED}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("tests.test_check_ref_resolution.ADR_DIR", adr_dir)
    monkeypatch.setattr("tests.test_check_ref_resolution.REQUIREMENTS", requirements)
    monkeypatch.setattr("tests.test_check_ref_resolution.TRACE", trace)

    # The synthetic search domain. The eroded ref is quoted by a synced review
    # report and by nothing else; the control ref is quoted by its own module's
    # docstring node-id table AND defined there, which is the shape the board's
    # four shim modules have.
    module = _SYNTHETIC_ERODED.partition("::")[0]
    review = "meta/review/19700101T000000Z-SYNTHETIC-cycle1.yml"
    files = {
        review: f"findings:\n  - the cell {_SYNTHETIC_ERODED} is cited here\n",
        module: (
            f'"""A synthetic module.\n\n* AC-SYN -- ``{_SYNTHETIC_DEFINED}``\n"""\n\n'
            "def test_synthetic_defined_node_id() -> None:\n    pass\n"
        ),
    }

    def synthetic_loose() -> dict[str, tuple[str, ...]]:
        """The real trie over a synthetic domain -- `_loose_resolution`'s body."""
        refs = tuple(declared.ref for declared in _declared_refs())
        pattern = _trie_pattern(refs)
        found: dict[str, set[str]] = {ref: set() for ref in refs}
        for name, text in files.items():
            for match in pattern.finditer(text):
                found[match.group(0)].add(name)
        return {ref: tuple(sorted(hits)) for ref, hits in found.items()}

    def synthetic_definitions() -> dict[str, tuple[str, ...]]:
        return {"test_synthetic_defined_node_id": (f"{module}:6",)}

    monkeypatch.setattr(
        "tests.test_check_ref_resolution._loose_resolution", synthetic_loose
    )
    monkeypatch.setattr(
        "tests.test_check_ref_resolution._definitions", synthetic_definitions
    )
    # `_verdicts` is memoised on the real board, so it is cleared on the way in
    # and on the way out: leaving a synthetic population cached would make every
    # later cell in this module assert against it.
    _verdicts.cache_clear()
    try:
        # The instrument, proved on the unmutated synthetic input first: both
        # refs derived, both classified as node ids, and each resolved the way
        # the fixture intends. A fixture that silently derived nothing would
        # satisfy every negative assertion below.
        derived = {verdict.ref: verdict for verdict in _verdicts()}
        assert set(derived) == {_SYNTHETIC_ERODED, _SYNTHETIC_DEFINED}, sorted(derived)
        for ref, verdict in derived.items():
            assert verdict.declared.form == FORM_NODE_ID, (ref, verdict.declared.form)
        assert derived[_SYNTHETIC_ERODED].loose == (review,), derived[_SYNTHETIC_ERODED]
        assert not derived[_SYNTHETIC_ERODED].strict, derived[_SYNTHETIC_ERODED]
        assert derived[_SYNTHETIC_DEFINED].strict == (f"{module}:6",), (
            derived[_SYNTHETIC_DEFINED]
        )

        eroded = {
            verdict.ref: verdict
            for verdict in _class_of(lambda v: v.bookkeeping_only)
        }
        assert _SYNTHETIC_ERODED in eroded, (
            f"the detector did not report a node-id ref that is declared by the "
            f"model, resolved only by {review} and defined nowhere -- which is "
            f"the erosion AC-4 is about. Reported instead: {sorted(eroded)}"
        )
        verdict = eroded[_SYNTHETIC_ERODED]
        assert not verdict.strict, f"expected no definition, found {verdict.strict}"
        assert all(hit.startswith("meta/review/") for hit in verdict.loose), (
            f"expected the review-YAML sync to be its only resolver; resolved by "
            f"{verdict.loose}"
        )
        # The control: the same form, same declaring authority, one `def`
        # apart. A detector that reports this one reports everything.
        assert _SYNTHETIC_DEFINED not in eroded, (
            f"a node-id ref with a real definition in the module it names was "
            f"reported as eroded: {derived[_SYNTHETIC_DEFINED]}"
        )
        assert not derived[_SYNTHETIC_DEFINED].falsely_alive
    finally:
        _verdicts.cache_clear()


def test_the_repaired_node_id_instance_stays_repaired() -> None:
    """The live half of AC-4's node-id case, in the direction that is monotone.

    :data:`_AC392_REF` was a member of the gate's class until CARD-285's merge
    defined it. Pinning that **repair** is safe where pinning the defect was
    not: a ``def`` does not disappear because a review report was synced in, so
    this cell cannot be killed by the board improving -- only by the board
    regressing, which is the whole point. If it ever reds, either the ``def``
    was deleted or renamed while the model goes on declaring the node id (the
    erosion, returning to the same ref), or the model stopped declaring it, and
    the two are distinguished here rather than left to a reader.
    """
    declared = {verdict.ref: verdict for verdict in _verdicts()}
    assert _AC392_REF in declared, (
        f"{_AC392_REF} is no longer declared by the model at all -- that moves "
        f"CENSUS, and it is not this cell's subject; re-derive the census"
    )
    verdict = declared[_AC392_REF]
    module = _AC392_REF.partition("::")[0]
    assert verdict.strict, (
        f"{_AC392_REF} has lost its definition: it was repaired by CARD-285's "
        f"merge and is eroded again. The model still declares it, so the "
        f"validator still reads it as checked."
    )
    assert any(site.rsplit(":", 1)[0] == module for site in verdict.strict), (
        f"{_AC392_REF} is defined, but not in the module its node id names: "
        f"{verdict.strict}"
    )
    assert not verdict.bookkeeping_only and not verdict.falsely_alive, verdict


# --- AC-3 / the guard does not absorb honest refs ---------------------------


def test_a_ref_with_a_real_definition_is_not_reported() -> None:
    """AC-3, first half.

    Derived rather than exemplified: *every* ref that resolves to a real
    ``def``/``class`` must be outside both the gate's class and the
    falsely-alive class. The count is asserted so the claim cannot be satisfied
    by an empty set.
    """
    defined = [verdict for verdict in _verdicts() if verdict.strict]
    # Exact, not a floor. The floor was `> 300` against a measured 382, so 82
    # refs could have stopped resolving to a definition with this cell still
    # green -- a control that cannot fail in the direction it is about.
    _assert_class("defined", DEFINED, tuple(defined))
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
        "requirements.yml:1 (check:)",
    ), "a review-lens check must contribute no ref rather than raise"


def test_the_trace_tests_lists_agree_with_an_independent_reading() -> None:
    """The census, held against a second reading of the same file.

    **The witness neither older self-check could be.** F-001 was a ``break`` on
    the first non-``- item`` line of a ``tests:`` list, so a ``#`` comment
    inside a list truncated it; 16 of ``trace.yml``'s 510 refs and 3 of the
    board's 579 (the census at the cut; it is 580 at HEAD) vanished with no
    exception raised. Both existing controls were
    blind to exactly that:

    * :func:`test_every_declared_ref_lands_in_exactly_one_class` compares the
      partition against ``len(_verdicts())`` -- both sides derived from the
      same truncated scan, so a dropped ref is absent from both and the cell
      stays green;
    * :func:`test_the_derivation_reads_all_four_authorities` asserted a floor of
      ``> 500`` against 576, which 494-from-``trace.yml`` never came near.

    A count is only evidence against an **independent** reading of the same
    bytes, so that is what this asserts: set equality, both directions, against
    :func:`_trace_tests_refs_by_backward_scan`, whose algorithm cannot be
    confused by any line *between* two items.

    Measured by replaying the bug -- the comment-survives branch of
    :func:`_tests_block` turned back into an early return, line count
    preserved, blob checked both sides, ``__pycache__`` swept: **3 failed, 16
    passed**, this cell naming all 16 dropped refs in its message, plus the
    control below and :data:`DEFINED`. The other six class baselines stay
    green, which is what "the non-movement was luck" means concretely.

    Two teeth, and the second earned its place: deleting the second
    implementation (``independent = set(primary)``) **survives on a clean
    tree**, because an instrument that agrees with itself looks exactly like
    one that agrees with something else. Replaying the bug *with* that deletion
    still reds, on :data:`TRACE_TESTS` -- the cross-reading catches the cause,
    the pinned counts catch the consequence, and neither alone is the witness.

    The whole-board census is pinned here too, for the plainest reason this card
    has: every figure this module and ADR-0039 state about the board has to be
    re-derivable, or it becomes another ADR-0006/R1 -- a number that read as
    checked because it was written down confidently.
    """
    primary = {
        declared.ref
        for declared in _declared_refs()
        if any(source.startswith("trace.yml:") for source in declared.sources)
    }
    independent = _trace_tests_refs_by_backward_scan()
    missing = sorted(independent - primary)
    extra = sorted(primary - independent)
    assert not missing and not extra, (
        f"the forward scan of trace.yml's tests: lists and the independent "
        f"backward reading of the same file disagree: {len(missing)} ref(s) the "
        f"backward reading sees and the scan does not ({missing}), "
        f"{len(extra)} the other way ({extra}). A ref the derivation cannot see "
        f"is a ref this module reports nothing about, and nothing else here "
        f"would notice -- every other count is derived from the same scan."
    )
    assert (len(primary), _fingerprint(tuple(primary))) == TRACE_TESTS, (
        f"trace.yml's tests: refs moved: {(len(primary), _fingerprint(tuple(primary)))} "
        f"against baseline {TRACE_TESTS}"
    )
    census = tuple(declared.ref for declared in _declared_refs())
    assert (len(census), _fingerprint(census)) == CENSUS, (
        f"the census moved: {(len(census), _fingerprint(census))} against "
        f"baseline {CENSUS}. Re-derive it before updating the baseline, and "
        f"check which authority moved -- a census that SHRINKS is how F-001 "
        f"looked from the inside."
    )


def test_a_non_item_line_inside_a_tests_list_is_classified_and_never_a_break() -> None:
    """The control for :func:`_tests_block`'s four cases (ADR-0039/R2).

    Without it the comment-survives branch is unexercised and "a comment does
    not end the list" is a comment about a comment. Each case is checked on a
    synthetic block, including the one that must RAISE -- because the whole
    defect was a shape that ended the scan instead of failing it.
    """
    item = "  - Synthetic" + "RefName_One"
    second = "  - Synthetic" + "RefName_Two"
    # A comment and a blank line between two items: both survive, both items
    # are collected. This is F-001's exact shape.
    assert _tests_block(["  tests:", item, "  # a note about a retired test", "", second], 0) == (
        item.strip()[2:],
        second.strip()[2:],
    )
    # A key at the list's own indentation ends it; a deeper item is still part
    # of it; a dedented item belongs to an outer sequence and ends it.
    assert _tests_block(["  tests:", item, "  notes: >-", "    prose", second], 0) == (
        item.strip()[2:],
    )
    assert len(_tests_block(["  tests:", item, "      - Deeper" + "RefName", second], 0)) == 3
    assert _tests_block(["  tests:", item, "- Outer" + "RefName"], 0) == (item.strip()[2:],)
    # And the unanalysable shape: indented, not an item, not a comment, not a
    # key. A break here is what dropped 16 refs; a raise is what ADR-0039/R2
    # asks for.
    try:
        _tests_block(["  tests:", item, "    a bare scalar continuation"], 0)
    except RefShapeNotClassifiable:
        pass
    else:
        raise AssertionError("an unanalysable line inside a tests: list was accepted")


def test_an_unreadable_declaration_key_shape_is_a_failure_and_not_a_skip(
    tmp_path, monkeypatch
) -> None:
    """The control for :func:`_refuse_unread_declaration_keys` (ADR-0039/R2).

    Review cycle 1's F-001 was a silent skip inside a block sequence. Cycle 2
    found the same rule broken one frame up, in the dispatch that decides whether
    the block is read at all, and the reason the cell that *claimed* to cover it
    could not is worth keeping in view: ``test_every_declared_check_is_classified``
    iterates the refs the derivation already produced, so a key whose shape was
    never read contributes nothing for it to look at. **This** cell drives the
    shapes at the derivation itself, which is the only place the raise is
    observable.

    Every shape is driven against a synthetic authority set in ``tmp_path``, so
    no tracked file is written at any point. The clean set is derived first and
    its refs asserted -- an instrument that raised on everything, or that
    collected nothing, would pass the six negative cases while proving nothing.
    """
    alpha = "Synthetic" + "Authority_Alpha"
    beta = "Synthetic" + "Authority_Beta"
    gamma = "Synthetic" + "Authority_Gamma"
    delta = "Synthetic" + "Authority_Delta"

    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    requirements = tmp_path / "requirements.yml"
    trace = tmp_path / "trace.yml"
    monkeypatch.setattr("tests.test_check_ref_resolution.ADR_DIR", adr_dir)
    monkeypatch.setattr("tests.test_check_ref_resolution.REQUIREMENTS", requirements)
    monkeypatch.setattr("tests.test_check_ref_resolution.TRACE", trace)

    def write(
        adr_body: str = "",
        requirements_body: str = "",
        trace_body: str = "",
        adr_tail: str = "",
    ) -> None:
        (adr_dir / "0001-synthetic.md").write_text(
            "# Synthetic ADR\n\n"
            "Prose outside a fence, wrapped so that a sentence begins with a word\n"
            f"tests: like this one, which declares nothing (the live shape at\n"
            "0042-book-interior-is-vector-cover-stays-raster.md:153).\n\n"
            "```yaml\n"
            "- id: SYN/R1\n"
            f"  check: {{kind: test, ref: {alpha}}}\n"
            f"{adr_body}"
            "```\n" + (f"\n{adr_tail}" if adr_tail else ""),
            encoding="utf-8",
        )
        requirements.write_text(
            "requirements:\n"
            "  - id: SYN-001\n"
            f"    test: {beta}\n"
            "    check:\n"
            "      kind: test\n"
            f"      ref: {gamma}\n"
            "    rationale: >-\n"
            "      a block scalar whose body wraps onto a line beginning\n"
            "      test: which is prose and declares nothing\n"
            f"{requirements_body}",
            encoding="utf-8",
        )
        trace.write_text(
            "covered:\n"
            "  - id: SYN-001\n"
            "    tests:\n"
            f"      - {delta}\n"
            "      # a note about a retired test\n"
            "    notes: >-\n"
            "      folded prose wrapping onto a line beginning\n"
            "      tests: which is prose and declares nothing\n"
            f"{trace_body}",
            encoding="utf-8",
        )

    # The instrument, proved on an unmutated input first: all four authorities
    # read, the two prose lines and the comment-in-list ignored, nothing raised.
    write()
    derived = {declared.ref: declared.sources for declared in _declared_refs()}
    assert set(derived) == {alpha, beta, gamma, delta}, derived
    # The source labels carry the LINE now, so each is asserted as the shape it
    # has rather than as a bare filename -- and the line is asserted to be the
    # one the declaration actually sits on, read back off disk.
    assert derived[alpha] == ("adr/0001-synthetic.md:9",), derived[alpha]
    assert derived[beta] == ("requirements.yml:3 (test:)",), derived[beta]
    assert derived[gamma] == ("requirements.yml:4 (check:)",), derived[gamma]
    assert derived[delta] == ("trace.yml:3",), derived[delta]

    planted = "Synthetic" + "Authority_Planted"

    def derive_and_classify() -> set[str]:
        """The derivation the board actually runs: read, then classify.

        ``Declared.form`` is a lazy property, so a shape whose garbage is
        COLLECTED rather than skipped raises one frame later, when a cell asks
        for its form -- which is what ``test_every_declared_check_is_classified``
        does. R2's property is "collected or raised, never skipped", so the check
        has to cover both routes or it mis-reports one of them. The first draft
        of this cell asserted that ``_declared_refs`` itself must raise, and it
        red on ``requirements.yml``'s ``test: [A,`` -- which is collected, not
        skipped. Where the raise comes from used to be a message-quality
        difference, and it was recorded in the table below rather than papered
        over: the key refusal named the file and LINE, the form refusal the shape
        and the declaring authority but **not** the line. Review cycle 3
        instrumented all 26 shapes and measured that split exactly -- 20 key-route
        refusals naming the correct line, 6 form-route refusals naming none --
        and it is closed now: :attr:`Declared.sources` carries
        ``<authority>:<line>``, so every route names a line and the loop below
        asserts the line rather than only the file.
        """
        declared = _declared_refs()
        for entry in declared:
            entry.form
        return {entry.ref for entry in declared}

    # THE MATRIX. Every authority's own declaration key, driven at each
    # YAML-legal shape of that key -- not just at the one authority cycle 2
    # caught. `route` records which frame refuses it: "key" is
    # _refuse_unread_declaration_keys, "form" is Declared.form, and "fence" is
    # _declaration_key_lines itself. All three name the file AND the line, and
    # the loop below asserts the line: review cycle 3 found it asserting only the
    # filename, so a regression that lost the line number kept the cell green.
    illegal = (
        ("trace.yml", "key", f"    tests: [{planted},\n      {planted}2]\n"),
        ("trace.yml", "key", f"    tests: >-\n      {planted}\n"),
        ("trace.yml", "key", f"    tests: {planted}\n"),
        ("trace.yml", "key", "    tests: # a note instead of a list\n"),
        ("trace.yml", "key", f"    tests: [{planted}] # a note\n"),
        ("trace.yml", "key", f"    tests: &anchor [{planted}]\n"),
        ("requirements.yml", "form", f"    test: [{planted},\n      {planted}2]\n"),
        ("requirements.yml", "form", f"    test: >-\n      {planted}\n"),
        ("requirements.yml", "form", "    test: # a note instead of a ref\n"),
        ("requirements.yml", "form", f"    test: [{planted}] # a note\n"),
        ("requirements.yml", "form", f"    test: &anchor {planted}\n"),
        ("requirements.yml", "form", f"    test: [{planted}]\n"),
        ("requirements.yml", "key", f"    test:\n      - {planted}\n"),
        ("requirements.yml", "key", f"    check: {{kind: test, ref: {planted}}}\n"),
        ("requirements.yml", "key", f"    check: >-\n      {planted}\n"),
        ("requirements.yml", "key", f"    check: {planted}\n"),
        ("requirements.yml", "key", "    check: # a note\n"),
        ("requirements.yml", "key", f"    check: [{planted}]\n"),
        ("requirements.yml", "key", f"    check: &anchor {planted}\n"),
        ("adr/0001-synthetic.md", "key", f"  check:\n    kind: test\n    ref: {planted}\n"),
        ("adr/0001-synthetic.md", "key", f"  check: >-\n    {planted}\n"),
        ("adr/0001-synthetic.md", "key", f"  check: {planted}\n"),
        ("adr/0001-synthetic.md", "key", "  check: # a note\n"),
        ("adr/0001-synthetic.md", "key", f"  check: [{planted}]\n"),
        ("adr/0001-synthetic.md", "key", f"  check: &anchor {planted}\n"),
        ("adr/0001-synthetic.md", "key", f"  check: {{kind: test,\n    ref: {planted}}}\n"),
    )
    # The legal shapes, asserted to still DERIVE their ref. Without these a
    # derivation that raised on absolutely everything would pass every negative
    # case above while reading nothing at all.
    legal = (
        ("trace.yml", f"    tests:\n      - {planted}\n"),
        ("trace.yml", f"    tests: [{planted}]\n"),
        ("requirements.yml", f"    test: {planted}\n"),
        ("requirements.yml", f"    check:\n      kind: test\n      ref: {planted}\n"),
    )
    # THE REGION ROWS -- review cycle 3's F-001c3. The region notion that both
    # halves of the derivation rest on was not TOTAL, and four shapes fell off
    # its edges: two in the silent direction, one inventing a ref out of prose,
    # one reddening the guard on English. All four were measured latent on the
    # real authorities, which is why they want controls here rather than a note:
    # latent is one registry edit away from live, and nothing else on this board
    # asserts that no authority grows one. `probe` is the line the refusal must
    # NAME, which is not always the body's first line -- an unclosed fence is
    # refused by the fence, not by the sentence it would otherwise have accused.
    region_illegal = (
        # (b) A ``~~~`` fence. Inside one the ADR refusal was silently skipped.
        # It is planted AFTER the template's own fence on purpose: inside a
        # backtick fence a ``~~~`` line is content, not a fence, so planting it
        # there would have tested nothing.
        (
            "adr/0001-synthetic.md",
            "key",
            "  check:",
            f"~~~yaml\n- id: SYN/R2\n  check:\n    kind: test\n    ref: {planted}\n~~~\n",
        ),
        # (c) An UNCLOSED fence. The whole remainder of the document then reads
        # as fenced, so the ordinary prose line below became a candidate and the
        # guard red on English -- the live shape being
        # 0042-book-interior-is-vector-cover-stays-raster.md:153. The assertion
        # that matters here is WHICH line the refusal names: the fence, not the
        # sentence.
        (
            "adr/0001-synthetic.md",
            "fence",
            "```yml",
            f"```yml\n- id: SYN/R2\n  check: {{kind: test, ref: {planted}}}\n\n"
            "And then prose after an unclosed fence, wrapped onto a line beginning\n"
            "tests: which declares nothing and must not be the thing refused.\n",
        ),
        # (d) A QUOTED declaration key: invisible to collection AND to refusal,
        # which is F-001c2's asymmetry un-closed for one spelling.
        ("trace.yml", "key", f'    "tests": [{planted}]', f'    "tests": [{planted}]\n'),
    )
    # (a) THE INVENTING DIRECTION, and the only rows here that assert the
    # opposite of a raise. A legal YAML block-scalar opener carrying a trailing
    # comment was not recognised as an opener, so its body was not prose and a
    # body line beginning ``test: `` whose text is a valid identifier was
    # COLLECTED as a declared ref -- census up by one, nothing raised. No
    # refusal can catch that direction: the default-deny fires only where no
    # narrow pattern claims, and invention happens exactly where one does. So
    # these rows assert that nothing raised AND that nothing was collected.
    prose = (
        ("requirements.yml", f"    rationale: >- # a note\n      test: {planted}\n"),
        ("trace.yml", f"    notes: |- # a note\n      tests: [{planted}]\n"),
    )

    def plant(label: str, body: str) -> None:
        if label == "trace.yml":
            write(trace_body="  - id: SYN-002\n" + body)
        elif label == "requirements.yml":
            write(requirements_body="  - id: SYN-002\n" + body)
        elif body.lstrip().startswith(("~~~", "```")):
            write(adr_tail=body)
        else:
            write(adr_body=body)

    def line_of(label: str, probe: str) -> int:
        """The 1-based line the refusal must name, read back off disk.

        Derived from the written file and not from the module, so a refusal that
        computed its line number the same wrong way cannot agree with this.
        """
        if label.startswith("adr/"):
            text = (adr_dir / "0001-synthetic.md").read_text(encoding="utf-8")
        elif label == "requirements.yml":
            text = requirements.read_text(encoding="utf-8")
        else:
            text = trace.read_text(encoding="utf-8")
        hits = [i for i, line in enumerate(text.splitlines(), 1) if line == probe]
        assert len(hits) == 1, f"the probe {probe!r} is not unique in {label}: {hits}"
        return hits[0]

    def drive(label: str, route: str, probe: str, body: str) -> None:
        plant(label, body)
        try:
            derive_and_classify()
        except RefShapeNotClassifiable as refusal:
            want = line_of(label, probe)
            # The LINE, not just the file. Review cycle 3 instrumented all 26
            # shapes and found every key-route refusal naming the correct line
            # while this loop checked only the FILENAME -- so a regression that
            # lost the line number would have kept the cell green, in the module
            # whose own subject is figures that read as checked. All three routes
            # name a line now: the key frame and the fence frame print
            # ``label:line`` themselves, and the form frame prints it through
            # :attr:`Declared.sources`.
            assert re.search(rf"{re.escape(label)}:{want}(?!\d)", str(refusal)), (
                body,
                f"expected {label}:{want}",
                str(refusal),
            )
            if route == "fence":
                assert "never closed" in str(refusal), (
                    f"an unclosed fence must be refused BY THE FENCE: {refusal}"
                )
        else:
            raise AssertionError(
                f"{label}: {body.strip()!r} was SILENTLY SKIPPED instead of "
                f"raising -- the shape contributed nothing, and nothing on this "
                f"board would have noticed. That is ADR-0039/R2's failure, one "
                f"frame above the frame review cycle 1 repaired."
            )

    for label, route, body in illegal:
        drive(label, route, body.splitlines()[0], body)
    for label, route, probe, body in region_illegal:
        drive(label, route, probe, body)

    for label, body in prose:
        plant(label, body)
        derived_now = derive_and_classify()
        assert derived_now == {alpha, beta, gamma, delta}, (
            f"{label}: {body.strip()!r} INVENTED a ref out of a block scalar's "
            f"prose -- {len(derived_now)} refs derived instead of 4: "
            f"{sorted(derived_now)}. A guard that invents a ref corrupts the "
            f"census in the direction no refusal on this board can see."
        )

    for label, body in legal:
        plant(label, body)
        derived_now = derive_and_classify()
        assert planted in derived_now, (
            f"{label}: the legal shape {body.strip()!r} derived no ref -- this "
            f"control would pass on a derivation that reads nothing: "
            f"{sorted(derived_now)}"
        )

    # And the ADR's block form specifically, which the ADR scan does not read at
    # all. 0 ADRs use one today, so this is the latent half -- latent is not the
    # same as absent.
    write(adr_body="  check:\n    kind: test\n    ref: " + planted + "\n")
    try:
        _declared_refs()
    except RefShapeNotClassifiable as refusal:
        assert "adr/0001-synthetic.md" in str(refusal), str(refusal)
    else:
        raise AssertionError("a block-form check: in an ADR was silently skipped")


def test_a_departed_member_is_recovered_by_name_and_its_departure_judged() -> None:
    """The control for :func:`_refuse_unexplained_departures` (F-002c2).

    The claim it carries is that a stored per-member digest set makes the
    repair-vs-signal-loss response **enforceable** while storing nothing a text
    search can resolve. A claim like that needs a control that can fail in the
    direction it is about, so all four cases are driven -- including the two that
    must stay GREEN, because a helper that red on every input would "pass" the
    negative case while proving nothing.

    Nothing here is written down: the planted departures are refs picked out of
    the derived population at run time, and the assertion is that the helper
    recovers the one that matters **by name** from a digest alone.
    """
    gate = _class_of(lambda v: v.bookkeeping_only)
    stored = _member_digests(tuple(verdict.ref for verdict in gate))
    assert len(stored) == len(gate), "per-member digests collided on the gate's class"

    # 1. Nothing departed: silent.
    _refuse_unexplained_departures("control", stored, gate)

    # 2. A departure that is NOT a repair -- a ref the validator still reads as
    #    alive and nothing defines. It must be named, from its digest alone.
    losses = [v for v in _verdicts() if v.falsely_alive and not v.bookkeeping_only]
    assert losses, "no falsely-alive non-gate ref exists; this case is unexercised"
    try:
        _refuse_unexplained_departures("control", stored | {_digest_of(losses[0].ref)}, gate)
    except AssertionError as refusal:
        assert losses[0].ref in str(refusal), (
            f"the departed member was not recovered by name: {refusal}"
        )
        assert "SIGNAL LOSS" in str(refusal), str(refusal)
    else:
        raise AssertionError(
            "a member that left without gaining a def/class was accepted silently"
        )

    # 3. A departure that IS a repair -- the ref carries a real def/class.
    repairs = [v for v in _verdicts() if v.strict and not v.bookkeeping_only]
    assert repairs, "no defined ref exists; this case is unexercised"
    _refuse_unexplained_departures("control", stored | {_digest_of(repairs[0].ref)}, gate)

    # 4. The honest residual: a digest matching no ref the model declares today.
    #    The declaration itself left, which moves CENSUS, so this cell must not
    #    claim to have judged it -- and must not be SILENT about it either, which
    #    is F-004c3. Before this control the helper returned with nothing
    #    reported at all on a PURE withdrawal, while its docstring claimed the
    #    count was reported "so the two cases are never confused": the count
    #    lived inside an assertion message that renders only when some other
    #    member also departed. The warning is the report; this is the control
    #    that reds if it goes away.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _refuse_unexplained_departures("control", stored | {"0" * 12}, gate)
    messages = [str(entry.message) for entry in caught]
    assert len(messages) == 1, (
        f"a pure withdrawal must be reported exactly once, got {len(messages)}: "
        f"{messages}"
    )
    assert "lost 1 member(s) whose digest matches no ref" in messages[0], messages
    assert "CENSUS" in messages[0], messages
    # And it must still not RAISE: a withdrawal is an honest residual, not a
    # signal loss, so the green half of the claim is asserted too. The filter is
    # "ignore" rather than absent so that this cell adds nothing to the suite's
    # warning count -- the warning is the helper's report to a human reading a
    # failure, not an event this run should look like it had.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _refuse_unexplained_departures("control", stored | {"0" * 12}, gate)


def test_the_cross_reading_cell_calls_the_second_reader_by_name() -> None:
    """The second reading cannot be silently replaced by a copy of the first.

    :func:`test_the_trace_tests_lists_agree_with_an_independent_reading` has a
    declared survivor: rewriting its body as ``independent = set(primary)``
    leaves it GREEN, because an instrument that agrees with itself looks exactly
    like one that agrees with something else. That insight is kept in that cell's
    own docstring and it is the right account of why the *assertion* cannot carry
    the claim -- but independence is a property of the SOURCE, and a source
    property is assertable. Measured: an ``ast`` walk of that cell's own
    ``FunctionDef`` yields ``_trace_tests_refs_by_backward_scan`` on a clean tree
    and does not after the rewrite.

    What this proves and does not: it pins the **call site**, not the
    algorithm's independence -- a future author could satisfy it with a second
    function that is a copy of the first. The evidence that the algorithms really
    differ is that three independent readings agree at 510 (the forward scan, the
    backward scan, and review cycle 2's indentation-stack walker run out of
    tree), plus the measured fact that the backward scan is strictly stronger on
    two of F-001c2's key shapes. House pattern, not a new idea:
    ``tests/test_guard_integrity.py`` AST-walks guard sources throughout and at
    one point parses its own ``__file__``.
    """
    module = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    cells = [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef)
        and node.name == "test_the_trace_tests_lists_agree_with_an_independent_reading"
    ]
    assert len(cells) == 1, f"expected exactly one cross-reading cell, found {len(cells)}"
    called = {node.id for node in ast.walk(cells[0]) if isinstance(node, ast.Name)}
    assert "_trace_tests_refs_by_backward_scan" in called, (
        "the cross-reading cell no longer calls the second reader -- it is "
        f"comparing the forward scan against something else, or against itself. "
        f"Names it uses: {sorted(called)}"
    )
    # And the control for the control: the cell must still use the forward
    # derivation too, or the comparison has lost its other side.
    assert "_declared_refs" in called, sorted(called)


def test_the_derivation_reads_all_four_authorities() -> None:
    """No authority is silently missing from the ref set.

    A ref declared only in ``trace.yml`` and nowhere else is still a ref the
    validator resolves, and an earlier census of this board missed both
    ``trace.yml`` and ``requirements.yml``'s block-form checks -- 424 refs
    instead of the 579 then on the board (580 at HEAD), which is a 27 % blind
    spot in a guard about blind spots.

    The floor below is deliberately left a floor: the census is pinned exactly,
    as :data:`CENSUS`, by
    :func:`test_the_trace_tests_lists_agree_with_an_independent_reading`. What
    this cell is for is the *source labels*, which that one does not check.
    """
    sources = {source for declared in _declared_refs() for source in declared.sources}
    # Every label is ``<authority>:<line>``, so these are prefix checks -- and
    # the line is what makes a form-route refusal actionable (F-002c3).
    assert any(source.startswith("adr/") for source in sources), sources
    assert any(source.endswith(" (test:)") for source in sources), sources
    assert any(source.endswith(" (check:)") for source in sources), sources
    assert any(source.startswith("trace.yml:") for source in sources), sources
    assert all(
        re.search(r":\d+(?: \((?:test|check):\))?\Z", source) for source in sources
    ), "a source label that names no line: " + repr(
        sorted(s for s in sources if not re.search(r":\d+(?: \((?:test|check):\))?\Z", s))
    )
    assert len(_declared_refs()) > 500, f"only {len(_declared_refs())} refs derived"
