"""nonogram — a CLI generator for uniquely-solvable black-and-white nonograms.

Package layout (ADR-0007, layered pipeline package; one bounded context,
CTX-001)::

    cli.py           COMP-001  the only inbound adapter (argparse)
    orchestrator.py  COMP-002  owns the Puzzle aggregate (AGG-001) and the
                               generation policies POL-001..POL-005
    sourcing/        COMP-003  CAP-001  (later card)
    clues.py         COMP-004  CAP-002  (later card)
    solver/          COMP-005  CAP-003  (later card)
    difficulty.py    COMP-006  CAP-004  (later card)
    export/          COMP-007  CAP-005  (later card)

Dependencies point inward only: ``cli`` imports ``orchestrator``, the
orchestrator imports the capability modules, and capability modules never
import ``cli`` nor each other laterally. This package's ``__init__`` therefore
re-exports nothing and imports no submodule — importing ``nonogram`` must never
drag the adapter in behind a capability module.
"""

__version__ = "0.1.0"
