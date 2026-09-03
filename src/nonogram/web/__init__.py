"""COMP-008 — the web UI adapter, the tool's second inbound surface (FR-017).

A *sibling* of :mod:`nonogram.cli`, not a layer above or below it (ADR-0019).
The two adapters are the same rank in ADR-0007's dependency graph and the same
two rules shape both. The single edge between them is ``cli`` importing this
package to launch it, because ADR-0008 keeps one console entry point and
``nonogram serve`` is a subcommand of it; the reverse — ``web`` importing
``cli`` — is a guard violation (``_LAUNCH_EDGE`` in ``tests/test_cli.py`` is an
ordered pair, not a mutual exemption).

*Direction* (ADR-0007): this package imports inward only, and never outward or
laterally. It imports the orchestrator, to hand it a request and get a puzzle
back; ``errors``, to catch the one hierarchy that pipeline raises; and the
difficulty and export registries, which ``pages.py`` reads to render the form's
choices. Nothing inward of this package ever imports back. The structural guard
in ``tests/test_cli.py`` knows exactly two adapter names — ``cli`` and ``web``
— at one rank, so a capability module still cannot import either of them, nor
another capability laterally.

*HTTP only* (ADR-0010, ADR-0019/R1, guardrail G-2): everything here is HTTP —
routing, rendering, request parsing, and the mapping of form fields onto
``orchestrator.GenerationRequest``. Not one domain rule lives here: a form
submitted with ``size=5000`` builds a request carrying 5000 and is rejected
inward by the same ``SizeOutOfRange`` the CLI surfaces, exactly as a
``--size 5000`` argv is — which is how AC-050's "the same domain error the CLI
would raise" is true by construction rather than by parallel maintenance. The
same holds for a density, a difficulty tier that does not exist, and a name
that is present but unusable.

Module layout, mirroring the concerns ADR-0020 names::

    server.py      the socket: loopback-only bind, the serve loop, shutdown
                   (``create_server`` binds, ``serve_on`` runs — two calls, so
                   ``cli`` can report a bind failure without also owning the
                   loop)
    handler.py     the router: one ``(method, path)`` table, one handler class
    submission.py  the mapping: one posted body -> one ``GenerationRequest``
    pages.py       the HTML: the form, the result page, the failure page

``GET /`` renders the form and ``POST /generate`` runs it: the request is
mapped, ``orchestrator.generate`` and ``orchestrator.export_puzzle`` are called
synchronously on the request thread (ADR-0021), and the answer is either the
files written or a structured failure page carrying the domain error's own
message (EC-003). Image upload is still CARD-021's — the form renders no file
control and the mapping never fills ``GenerationRequest.image`` — so an
``image``-mode submission fails inward with the missing-``--image`` error, which
is the right answer to it (AC-008).

A method with no ``do_*`` at all still gets a ``501``. The *status* is the
standard library's, but the *response* is this package's:
:meth:`handler.WebUIRequestHandler.send_error` writes it, so it reads
``HTTP/1.0 501 Not Implemented`` as ``text/plain`` with ``nosniff`` and echoes
nothing off the wire, where the stdlib's own would have replied
``501 Unsupported method ('PUT')`` as ``text/html``.

Access control is three checks in :mod:`nonogram.web.handler` — the bind
address, the ``Host`` header, and the authority and fetch-metadata a request
claims — and no authentication at all: the server listens on 127.0.0.1 only,
refuses a ``Host`` naming anything else, refuses a request some other page
started, and reads no credential (NFR-003, NFR-004, CON-009, CON-010, AC-052,
AC-053, AC-054..AC-058, BCON-0001). The absence of an auth check is the
decision, not an oversight.

The three close three different reaches and none substitutes for another. The
bind stops a network peer. The ``Host`` check stops DNS rebinding — a request
steered here under a name an attacker controls that resolves to loopback. The
cross-origin refusal stops what neither of the first two can see: a browser
sets ``Host`` from the request's *target*, so a form on any origin posting to
``http://127.0.0.1:<port>/generate`` arrives with an allowlisted ``Host`` over
a loopback socket, and until CARD-020's cycle-1 review it was served — which,
once ``POST /generate`` existed, meant running the pipeline and writing files
at a path the attacking page chose. What is read instead are the two headers a
browser attaches to such a request and page script can neither forge nor
suppress, ``Sec-Fetch-Site`` and ``Origin``, plus the authority of an
absolute-form request target. A request carrying none of the three — ``curl``,
a typed URL, an HTTP/1.0 probe — is served, so nothing about the loopback
command-line flow changes.
"""

from __future__ import annotations

from nonogram.web.server import DEFAULT_PORT, LOOPBACK_HOST, create_server, serve_on

__all__ = ["DEFAULT_PORT", "LOOPBACK_HOST", "create_server", "serve_on"]
