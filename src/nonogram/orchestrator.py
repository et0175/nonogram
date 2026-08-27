"""COMP-002 — the pipeline orchestrator (skeleton only; body: CARD-005).

ADR-0007 gives this module three jobs, none of which is implemented yet:

* own the Puzzle aggregate (AGG-001) for the whole of one generation run;
* be the single enforcement point for INV-002 (a puzzle is exportable only
  after its uniqueness check confirmed exactly one solution) and INV-003 (the
  regenerate / resample / pixel-nudge counter never exceeds its bound);
* drive the generation policies POL-001..POL-005 by composing the capability
  modules (sourcing, clues, solver, difficulty, export), which never call each
  other laterally.

Dependency direction: this module must never import ``nonogram.cli``. The
adapter depends on the orchestrator; the reverse import would invert the one
structural rule ADR-0007 fixes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["GenerationRequest", "Puzzle", "generate"]


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """One generation run as the caller asked for it — an unvalidated intent.

    This is the CLI/domain boundary type: the adapter fills it straight from
    the parsed argv and hands it inward. Its fields are therefore *syntactically*
    typed and widely optional on purpose — ``size`` and ``density`` are plain
    integers in whatever range the user typed, and ``mode`` is a plain string.
    Nothing here has been checked against a domain rule yet; resolving defaults
    and rejecting out-of-range values is the domain's job, inward of COMP-001
    (ADR-0010, guardrail G-3).

    Later cards extend this record alongside the parser it mirrors
    (``difficulty``, ``name``, ``image``, further export formats).
    """

    mode: str
    size: int | None = None
    density: int | None = None
    seed: int | None = None
    export_formats: tuple[str, ...] = ()
    out: Path | None = None


class Puzzle:
    """AGG-001 — one puzzle-generation attempt. Placeholder; fields: CARD-005.

    The aggregate carries a single attempt from source grid through clue
    computation, uniqueness verification, difficulty scoring and export, across
    all of its regenerate / resample / nudge retries — it is not re-created per
    retry, which is why INV-003's counter is one invariant on one aggregate.
    Its state and the invariants INV-001..INV-003 that constrain it land with
    the generation pipeline in CARD-005; declaring speculative fields here would
    only pre-empt that card, so this body is intentionally empty.
    """


def generate(request: GenerationRequest) -> Puzzle:
    """Run one generation attempt end to end and return the finished puzzle.

    Body: CARD-005. Raises the ``nonogram.errors`` domain errors — including
    ``GenerationAbandoned`` (POL-005) and ``SolverTimeout`` (ADR-0011) — which
    the CLI adapter maps onto exit codes.
    """
    raise NotImplementedError(
        "The generation pipeline is not implemented yet (CARD-005 owns "
        "orchestrator.generate; CARD-001 only establishes its signature)."
    )
