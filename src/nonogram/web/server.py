"""The socket: a loopback-only ``ThreadingHTTPServer`` and its serve loop.

The one load-bearing line in this module is the bind address, and it is a
literal (ADR-0020, NFR-003, BCON-0001)::

    LoopbackHTTPServer((LOOPBACK_HOST, port), WebUIRequestHandler)

ADR-0020 records that as a *required consequence* rather than a framework
default, for a reason worth restating: a default can change under you between
releases, and a default is not checkable. A constant that no parameter,
environment variable or keyword argument can override is both. There is
deliberately no ``host=`` argument on :func:`create_server` or :func:`serve` —
adding one would turn AC-052 from a property of the code into a property of how
it happens to be called (F-9).

Threading, from ``ThreadingHTTPServer``, is not about concurrency: BCON-0001
forbids a second user and ADR-0021 relies on there being exactly one generation
in flight. It is about a single browser opening a second connection (a
favicon request, a reload) not deadlocking behind a 30-second generation on the
first one.
"""

from __future__ import annotations

import sys
from http.server import ThreadingHTTPServer

from nonogram.web.handler import WebUIRequestHandler

__all__ = ["DEFAULT_PORT", "LOOPBACK_HOST", "LoopbackHTTPServer", "create_server", "serve"]

#: The only interface this server ever listens on (NFR-003, AC-052,
#: BCON-0001). A module constant, not a parameter — see the module docstring.
LOOPBACK_HOST = "127.0.0.1"

#: Default TCP port for ``nonogram serve``. High, fixed, and outside the
#: privileged range so the server never needs elevation; ``--port`` overrides
#: it, and ``--port 0`` asks the kernel for any free port (which is how the
#: tests bind without racing each other for a fixed one).
DEFAULT_PORT = 8765


class LoopbackHTTPServer(ThreadingHTTPServer):
    """``ThreadingHTTPServer`` that does not shout about a dropped connection.

    A browser that navigates away, reloads, or hits Stop mid-response closes
    the socket under the handler, and the ``BrokenPipeError`` /
    ``ConnectionResetError`` that follows reaches
    ``socketserver.BaseServer.handle_error``, whose stdlib implementation
    prints a full traceback. For a local single-user tool that is a routine
    event printed as if it were a crash (F-3).

    The override narrows *only* that case. Everything else keeps the stdlib's
    traceback, because anything else genuinely is a bug in this adapter and a
    quiet one-liner would hide it.
    """

    def handle_error(self, request: object, client_address: object) -> None:
        """Report a lost connection in one line; defer otherwise."""
        if isinstance(sys.exception(), ConnectionError):
            print(f"nonogram: client {client_address} disconnected", file=sys.stderr)
            return
        super().handle_error(request, client_address)  # type: ignore[arg-type]


def create_server(port: int = DEFAULT_PORT) -> LoopbackHTTPServer:
    """Bind the web UI's listening socket to loopback on ``port``.

    Returns an unstarted server; the caller owns ``serve_forever`` and
    ``server_close``. Split out from :func:`serve` so a test can drive a real
    socket without also owning a blocking loop — which is what lets AC-052
    check the bound interface behaviourally rather than by reading back a
    constructor argument.

    Nothing is caught here. A busy port, a privileged port, or a ``port``
    outside 0..65535 raises the standard library's own ``OSError`` (or
    ``OverflowError``, which is what the socket layer raises for the last case
    — notably *not* an ``OSError``), and it propagates unwrapped: a socket that
    will not bind is not a domain failure and does not become a
    ``NonogramError`` (guardrails G-2, G-4). ``cli.py`` is the single place
    that turns it into a message and an exit code (F-1, F-2).
    """
    return LoopbackHTTPServer((LOOPBACK_HOST, port), WebUIRequestHandler)


def serve(port: int = DEFAULT_PORT) -> None:
    """Serve the web UI until interrupted, then release the port.

    ``Ctrl-C`` arrives as a ``KeyboardInterrupt`` inside ``serve_forever`` and
    is a deliberate stop, not a failure: it is swallowed here and
    ``nonogram serve`` exits 0 (F-6). The ``finally`` closes the listening
    socket on every path out, including an exception this function does not
    expect, so the port is never left held by a dying process.

    In-flight requests are not awaited. ``ThreadingHTTPServer`` runs its
    handlers on daemon threads and ``socketserver``'s join tracks only
    non-daemon ones, so ``server_close`` returns immediately and a generation
    still running is abandoned — the same accepted outcome ADR-0021 already
    records for a browser that times out first.
    """
    server = create_server(port)
    print(f"serving on http://{LOOPBACK_HOST}:{server.server_port}/ — press Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
