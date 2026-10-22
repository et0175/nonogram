"""nonogram — a CLI generator for uniquely-solvable black-and-white nonograms.

This docstring is the canonical component map, and since CARD-261 the only one:
CLAUDE.md points here instead of keeping a second copy. ``tests/test_cli.py``'s
``TestComponentMap_*`` classes hold the row set below to the modules ADR-0007's
import walk enumerates on disk, in both directions — a component with no row
and a row with no module each fail the suite. What they do not hold is a row's
*description*; that stays a human reading.

The pipeline (ADR-0007, layered pipeline package; one bounded context,
CTX-001)::

    cli.py           COMP-001  inbound adapter (argparse); parsing only, no
                               domain validation
    web/             COMP-008  inbound adapter (HTTP, stdlib ``http.server``),
                               a sibling of cli.py in the same process,
                               launched by ``nonogram serve``
    orchestrator.py  COMP-002  owns the Puzzle aggregate (AGG-001) and the
                               generation policies POL-001..POL-005; drives the
                               capability modules below
    sourcing/        COMP-003  CAP-001  sources a solution grid:
                               ``random_grid.py``, ``library.py`` with its
                               ``templates/``, and ``image.py``
    clues.py         COMP-004  CAP-002  pure run-length-encoding of a grid into
                               row and column clues
    solver/          COMP-005  CAP-003  hand-rolled constraint-propagation plus
                               backtracking uniqueness solver
    difficulty.py    COMP-006  CAP-004  scores 0..100 from the solver's rung
                               tags, then the Easy/Medium/Hard bands
    export/          COMP-007  CAP-005  PNG/SVG/JSON/CSV/PDF renderers, plus
                               ``layout.py``'s shared page geometry
    errors.py                  the flat exception hierarchy every layer raises
                               from; imports nothing itself
    limits.py                  the supported grid-size range, ``MIN_SIZE`` and
                               ``MAX_SIZE``; imports nothing itself

``errors.py`` and ``limits.py`` are shared by all of the above, and are the
only modules a capability may import besides its own internals.

Beside the pipeline, with component ids of their own since CARD-110
(2026-09-22)::

    admin/           COMP-009  the Flask admin panel — batches, review, books,
                               PDFs; a third inbound adapter running in its own
                               process, outside ADR-0019's two
    db/              COMP-010  its SQLAlchemy models and session factory

``admin/`` imports ``db/`` and never the reverse, and nothing in ``cli``,
``web/`` or ``orchestrator`` reaches either (grep-verified, CARD-110) — which
is why they are two components rather than one, and why the pipeline above
neither sees nor depends on them.

Also in the tree and deliberately **not** a component (CARD-053)::

    analysis/                  ``quality_metric.py``, measured by
                               ``admin/app.py`` (CARD-050);
                               ``strategy_counter.py``, a prototype of the
                               scoring design in
                               docs/REQUIREMENTS/DIFFICULTY_ENGINE.md that
                               nothing on the shipping path calls (CARD-053
                               kept it deliberately — the rescoring question it
                               belongs to is still open)

It carries a row all the same. The row set is derived from the package rather
than from a list of component ids, so a directory the walk finds and this map
does not name fails whether or not anyone decided to call it a component.

"There are exactly two adapters (ADR-0019)" below describes the *pipeline's*
adapters, not a count of every entry point in the tree: ``admin/`` is a third
one, outside ADR-0019's scope as written.

Dependencies point inward only: the two pipeline adapters import
``orchestrator``, the orchestrator imports the capability modules, and
capability modules never import an adapter nor each other laterally. There are
exactly two adapters (ADR-0019) and they do not call each other; the single
exception is that ``cli`` imports ``web`` to launch it, because ADR-0008 keeps
one console entry point and ``nonogram serve`` is a subcommand of it. This
package's ``__init__`` therefore re-exports nothing and imports no submodule —
importing ``nonogram`` must never drag an adapter in behind a capability
module.
"""

__version__ = "0.1.0"
