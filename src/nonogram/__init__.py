"""nonogram — a CLI generator for uniquely-solvable black-and-white nonograms.

Package layout (ADR-0007, layered pipeline package; one bounded context,
CTX-001)::

    cli.py           COMP-001  inbound adapter (argparse)
    web/             COMP-008  inbound adapter (HTTP), sibling of cli.py
    orchestrator.py  COMP-002  owns the Puzzle aggregate (AGG-001) and the
                               generation policies POL-001..POL-005
    sourcing/        COMP-003  CAP-001  (later card)
    clues.py         COMP-004  CAP-002  (later card)
    solver/          COMP-005  CAP-003  (later card)
    difficulty.py    COMP-006  CAP-004  (later card)
    export/          COMP-007  CAP-005  (later card)

Shared by all of the above, and importing nothing themselves: ``errors.py``
(a flat exception hierarchy) and ``limits.py`` (the supported grid-size range).

Beside the pipeline, with component ids of their own since CARD-110
(2026-09-22)::

    admin/           COMP-009  the Flask admin panel — batches, review, books,
                               PDFs; a third inbound adapter, outside
                               ADR-0019's two
    db/              COMP-010  its SQLAlchemy models and session factory

``admin/`` imports ``db/`` and never the reverse, and nothing in ``cli``,
``web/`` or ``orchestrator`` reaches either (grep-verified, CARD-110) — which
is why they are two components rather than one, and why the pipeline above
neither sees nor depends on them.

Also in the tree and deliberately **not** a component (CARD-053)::

    analysis/        quality_metric.py, measured by admin/app.py (CARD-050);
                     strategy_counter.py, a prototype of the scoring design in
                     docs/REQUIREMENTS/DIFFICULTY_ENGINE.md that nothing on the
                     shipping path calls (CARD-053 kept it deliberately — the
                     rescoring question it belongs to is still open)

"There are exactly two adapters (ADR-0019)" below describes the *pipeline's*
adapters, not a count of every entry point in the tree: ``admin/`` is a third
one, outside ADR-0019's scope as written.

Dependencies point inward only: the two adapters import ``orchestrator``, the
orchestrator imports the capability modules, and capability modules never
import an adapter nor each other laterally. There are exactly two adapters
(ADR-0019) and they do not call each other; the single exception is that
``cli`` imports ``web`` to launch it, because ADR-0008 keeps one console entry
point and ``nonogram serve`` is a subcommand of it. This package's ``__init__``
therefore re-exports nothing and imports no submodule — importing ``nonogram``
must never drag an adapter in behind a capability module.
"""

__version__ = "0.1.0"
