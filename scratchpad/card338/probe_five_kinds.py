"""CARD-338's session probe: **all five convertible interior kinds** go vector,
and every default-constructed generator is assembled.

Not a test and not under ``tests/`` (G-2). Loaded with ``-p`` so the lift
happens **before any test module imports**, which is the state CARD-322's
conversion will actually produce.

CARD-329's ``scratchpad/card329/probe_puzzle_operators.py`` is the pattern and
deliberately not the import (a sibling card's scratchpad is not a dependency).
It lifts ``PageKind.PUZZLE`` alone, and its docstring says why: the other
interior kinds are drawn by writers that live downstream of
``book_pdf_generator``, so lifting them under a plain ``BookPDFGenerator(book)``
"would measure a REFUSAL, not a converted page, and that is a different
experiment".

**That reason has stopped being true.** The refusal is one line —
``book_pdf_generator.BookPDFGenerator.__init__`` reads the module global
``NO_DOWNSTREAM_WRITERS`` when ``pages is None`` — and CARD-309's assembly
point already exports the full set as
``book_interior_vector.DOWNSTREAM_WRITERS``. That module is downstream of all
five writers and **nothing in ``src/`` imports it**, which is what keeps the
dependency a direction rather than a loop; rebinding the generator's default
to it in one process makes every ``BookPDFGenerator(book)`` assembled. So this
probe does two things:

1. lifts the five declarations whose ``expires_with`` names CARD-322 —
   ``PUZZLE``, ``TITLE``, ``GUIDE``, ``TOC``, ``ANSWER``. ``COVER`` is not
   lifted (a photograph, raster by ADR-0042/R2 with an empty ``expires_with``)
   and neither is ``DIVIDER`` (``expires_with`` names CARD-231, which replaces
   the page rather than converting it). The five are **derived** from
   ``expires_with``, not listed, and a kind that stops naming CARD-322 is a
   refusal below rather than a silently narrower census;
2. rebinds the generator's default writer set to the assembly point's, so the
   four downstream kinds are *drawn* instead of refused.

``src/`` is read, never edited (G-1): both mutations are to imported module
objects for one process, and the files on disk are untouched.

**It cannot silently measure nothing (AC-1).** Every step is asserted, and the
assertion names what it could not do:

* each of the five kinds must have had a declaration to lift — a kind already
  absent means the tree is partly converted and the census would be measured
  against a different tree than it claims;
* ``page_medium`` must answer ``VECTOR`` for each after the lift — if it stops
  reading the registry, the lift is cosmetic;
* the rebinding target must exist by name on **both** modules, must be a full
  set (no field ``None``), and a default-constructed generator must actually
  come out holding it — a rename, a refactor to a factory, or a constructor
  that stops reading the global all make the rebinding a no-op that would
  otherwise run the session green over an unconverted tree;
* ``COVER`` and ``DIVIDER`` must still be declared raster afterwards, so a
  probe that emptied the registry outright is not mistaken for this one.
"""

from __future__ import annotations

from nonogram.admin import book_pdf_generator as generator
from nonogram.admin import book_interior_vector as assembly

#: The card that owns the conversion of the kinds this probe lifts. The five
#: are derived from the registry's own ``expires_with``, so this probe lifts
#: exactly the end state CARD-322 produces and cannot drift from it.
CONVERTED_BY = "CARD-322"

#: The name of the generator's default writer set, as a string, because the
#: whole point of the check is that the **name** may have gone.
TARGET = "NO_DOWNSTREAM_WRITERS"
SOURCE = "DOWNSTREAM_WRITERS"

#: The same set stated a second, independent way: the five kind names this
#: card's census is priced against. The probe asserts the two agree, so a
#: declaration that is already gone, or one whose ``expires_with`` was
#: re-pointed, is a **refusal naming the kind** rather than a quietly narrower
#: census. Two independent statements of one set is this tree's own discipline
#: (the solver's two brute-force counters; CARD-329's two transcriptions of one
#: population filter).
EXPECTED = frozenset({"PUZZLE", "TITLE", "GUIDE", "TOC", "ANSWER"})


def lifted_kinds() -> tuple:
    """The kinds to lift, derived from ``expires_with`` and cross-checked."""
    kinds = tuple(
        kind
        for kind, entry in generator._RASTER_DECLARATIONS.items()
        if CONVERTED_BY in entry.expires_with
    )
    derived = {kind.name for kind in kinds}
    missing = sorted(EXPECTED - derived)
    extra = sorted(derived - EXPECTED)
    assert not missing, (
        f"the probe found no declaration to lift for {missing}: either that "
        f"kind is already converted ({CONVERTED_BY} has landed, in part or in "
        "whole), or its expires_with no longer names that card. Either way the "
        "end state this probe stands up is not the five-kind one the census is "
        f"priced against (it would lift {sorted(derived)})"
    )
    assert not extra, (
        f"{extra} now names {CONVERTED_BY} in expires_with and the census is "
        "not priced for it: a sixth kind converting is a finding, not a wider "
        "probe"
    )
    return kinds


def _rebind_writers() -> None:
    """Make every default-constructed generator assembled, loudly."""
    assert hasattr(generator, TARGET), (
        f"the probe cannot rebind {generator.__name__}.{TARGET}: no such name. "
        "The generator's default writer set has been renamed or removed, so "
        "the four downstream kinds would be REFUSED and this probe would "
        "measure a refusal rather than a converted page"
    )
    assert hasattr(assembly, SOURCE), (
        f"the probe cannot read {assembly.__name__}.{SOURCE}: no such name. "
        "CARD-309's assembly point no longer exports a full writer set, so "
        "there is nothing to rebind the generator's default to"
    )
    writers = getattr(assembly, SOURCE)
    missing = [
        field
        for field in ("guide", "toc", "answer", "packed_answer")
        if getattr(writers, field, None) is None
    ]
    assert not missing, (
        f"{assembly.__name__}.{SOURCE} has no writer for {missing}: a partial "
        "set would refuse those kinds, and a refusal is not a converted page"
    )
    setattr(generator, TARGET, writers)
    # The constructor must actually read the global. If it has been changed to
    # a factory call, a default argument or a class attribute, the rebinding
    # above is a no-op and every census number would be measured against the
    # unconverted tree while reading green.
    built = generator.BookPDFGenerator(None)
    assert built.pages is writers, (
        f"a default-constructed BookPDFGenerator does not hold the rebound "
        f"writer set (got {built.pages!r}): __init__ no longer reads the module "
        f"global {TARGET}, so rebinding it changes nothing and this probe "
        "measures nothing"
    )


def pytest_configure(config):
    kinds = lifted_kinds()
    for kind in kinds:
        removed = generator._RASTER_DECLARATIONS.pop(kind, None)
        assert removed is not None, (
            f"the probe found no {kind.name} declaration to lift: either the "
            f"tree is already converted for that kind ({CONVERTED_BY} has "
            "landed, in part or in whole) or the registry moved -- either way "
            "this census would not be measured against the tree it names"
        )
        assert generator.page_medium(kind) is generator.PageMedium.VECTOR, (
            f"the lift did not change {kind.name}'s medium: page_medium no "
            "longer reads _RASTER_DECLARATIONS and this probe measures nothing"
        )
    still_raster = sorted(k.name for k in generator._RASTER_DECLARATIONS)
    assert still_raster == ["COVER", "DIVIDER"], (
        f"after the lift the registry declares {still_raster} raster, not "
        "['COVER', 'DIVIDER']: COVER is a photograph (empty expires_with) and "
        "DIVIDER is CARD-231's replacement, and a probe that emptied the "
        "registry outright measures a tree no card produces"
    )
    _rebind_writers()
    config.five_kind_probe = tuple(kind.name for kind in kinds)
