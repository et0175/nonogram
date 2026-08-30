"""COMP-008 — the web UI adapter, the tool's second inbound surface (FR-017).

A *sibling* of :mod:`nonogram.cli`, not a layer above or below it (ADR-0019).
The two adapters are the same rank in ADR-0007's dependency graph and the same
two rules shape both. The single edge between them is ``cli`` importing this
package to launch it, because ADR-0008 keeps one console entry point and
``nonogram serve`` is a subcommand of it; the reverse — ``web`` importing
``cli`` — is a guard violation (``_LAUNCH_EDGE`` in ``tests/test_cli.py`` is an
ordered pair, not a mutual exemption).

*Direction* (ADR-0007): this package imports inward only, and never outward or
laterally. What it imports today is the difficulty and export registries
(``pages.py`` reads them to render the form's choices); the orchestrator is
inward of it too and it is *permitted* to import it, but as shipped it does
not — there is nothing yet to hand the orchestrator. Nothing inward of this
package ever imports back. The structural guard in ``tests/test_cli.py`` knows
exactly two adapter names — ``cli`` and ``web`` — at one rank, so a capability
module still cannot import either of them, nor another capability laterally.

*HTTP only* (ADR-0010, ADR-0019/R1, guardrail G-4): everything here is HTTP.
Today that is routing and rendering; request parsing and the mapping of form
fields onto ``orchestrator.GenerationRequest`` are CARD-020's, excluded from
this package by CARD-019's guardrail G-5 and not present in it. Not one domain
rule lives here, and none will: when CARD-020 adds the mapping, a form
submitted with ``size=5000`` is to build a request carrying 5000 and be
rejected inward by the same ``SizeOutOfRange`` the CLI surfaces, exactly as a
``--size 5000`` argv would be — which is how AC-050's "the same domain error
the CLI would raise" becomes true by construction rather than by parallel
maintenance. That is a statement about the card that adds the code, not about
this one.

Module layout, mirroring the concerns ADR-0020 names::

    server.py   the socket: loopback-only bind, the serve loop, shutdown
                (``create_server`` binds, ``serve_on`` runs — two calls, so
                ``cli`` can report a bind failure without also owning the loop)
    handler.py  the router: one ``(method, path)`` table, one handler class
    pages.py    the HTML: the form page as a string constant (no templating)

Scope of *this* card (CARD-019): ``GET /`` renders the form. Submitting it is
CARD-020's (``POST /generate`` plus a result page) and image upload is
CARD-021's; until then a ``POST`` gets the standard library's own ``501``.

Access control is the bind address and nothing else: the server listens on
127.0.0.1 only and enforces no authentication at all (NFR-003, AC-052, AC-053,
BCON-0001). The absence of an auth check is the decision, not an oversight.
"""

from __future__ import annotations

from nonogram.web.server import DEFAULT_PORT, LOOPBACK_HOST, create_server, serve_on

__all__ = ["DEFAULT_PORT", "LOOPBACK_HOST", "create_server", "serve_on"]
