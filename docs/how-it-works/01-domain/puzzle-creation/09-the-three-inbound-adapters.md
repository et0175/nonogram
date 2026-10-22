# 09 — The three inbound adapters (COMP-001, COMP-008, COMP-009)

> Scope: `cli.py` (573 lines), `web/` (2,835), and the *door* of `admin/` —
> binding, credential and cross-site refusal. The panel's domain behaviour is in
> [07](07-book-assembly-and-the-admin-panel.md).
>
> **These are siblings with different constraints.** Do not read one's rules onto
> another: the CLI has no network surface at all, the web UI's entire access
> control is a loopback bind, and the admin panel has one credentialed door that
> *replaces* the loopback rule rather than adding to it.

## Why three, and why the guard lists them by name

ADR-0019 made the web UI a **sibling** of the CLI rather than a layer around it,
and ADR-0008 kept exactly one `[project.scripts]` console entry point — so
`nonogram serve` is a subcommand of `nonogram`, "one command, two subcommands, two
adapters behind them" (`cli.py:7`). The admin panel is a **third**, outside
ADR-0019's scope as written, with its own entry point and its own process.

`src/nonogram/__init__.py:40` is careful about that sentence: "'There are exactly
two adapters (ADR-0019)' below describes the *pipeline's* adapters, not a count of
every entry point in the tree."

The import guard lists the adapter rank by name rather than by pattern, and the
comment above `_ADAPTERS` in `tests/test_cli.py` says why: **"A guard with an
allowlist is weaker than a guard without one (ADR-0019, Negative), so the set
below is closed and is deliberately not a pattern: it grows only by a deliberate
edit to that line, reviewed as the architectural change admitting an adapter
is."**

```python
_ADAPTERS = frozenset({"cli", "web", "admin"})   # tests/test_cli.py:747
_LAUNCH_EDGE = ("cli", "web")                    # :760 — the only same-rank import
```

> **The guard's prose contradicted its own code until CARD-264.** The comment
> above `_ADAPTERS` said the set "is closed at **two** names", the test that pins
> it was called `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`,
> and that test's first line repeated the count — while the assertion underneath
> had read `_ADAPTERS == {"cli", "web", "admin"}` ever since `admin` was admitted.
> The mechanism was intact throughout and the pin did its job; only the prose
> lagged. It stopped being cosmetic when CARD-261 pointed a `CLAUDE.md` reader
> straight at that line: a reader who found the correct members under prose
> claiming fewer, and concluded `admin` was the erosion, would have deleted a
> correct entry. All three now state the *rule* — the set is closed and grows
> only by a deliberate edit to that line — and
> `TestAdapterAllowlist_NoProseClaimsAStaleCount` reds if any prose around the
> set states a count again, reading `len(_ADAPTERS)` for the number rather than
> restating it.
>
> **One site of the same claim is still open:** `web/__init__.py`'s package
> docstring says the structural guard "knows exactly two adapter names — `cli`
> and `web`". CARD-264 edits no file under `src/`, so it was measured and left;
> `CLAUDE.md`'s copy was removed by CARD-261. Note that
> `src/nonogram/__init__.py`'s "There are exactly two adapters (ADR-0019)" is a
> *different* and deliberate statement, qualified in the docstring itself as
> describing the pipeline's adapters rather than every entry point in the tree.

## COMP-001 — the CLI

Two rules shape `cli.py` (`:10`): **direction** (it imports the orchestrator and
nothing inward imports back) and **parsing only** (ADR-0010 guardrail G-3).

The second is the interesting one, and `_extent_token` (`:126`) is the worked
example of where the line sits. Splitting `30x20` into two numbers is syntax and
belongs here; whether 30 and 20 are supported sides is a rule about puzzles and
belongs to `sourcing.random_grid.validate_extent`. The function applies **no range
check**, deliberately: `"40x20"`, `"0"`, `"9"`, `"31"` and `"-5"` all parse and all
are refused inward, "with the tool's own message and exit code 3, rather than by
argparse with a usage error and exit code 2."

CARD-033 moved the line one step further in the same direction: a bare `--size 30`
now parses to `(30, None)` rather than `(30, 30)`, because deciding what an
unstated dimension should be is a domain question "and one whose answer depends on
the source, which this adapter cannot see."

So the flags carry no domain constraints at all:

| Flag | What argparse does | Where the rule lives |
|---|---|---|
| `--size N\|WxH` | `type=_extent_token` — shape only | `random_grid.validate_extent` / `derive_extent` |
| `--density PERCENT` | `type=int` | `random_grid.validate_density` (1..99) |
| `--library-key KEY` | nothing; **no `choices=`** | `library.template_for` → `UnknownLibraryImage` (AC-006) |
| `--image PATH` | `type=Path` and nothing else | `image.load_greyscale` → `UnreadableImage` (AC-008) |
| `--name NAME` | nothing | `NameContext.name_for` → `InvalidPuzzleName` (AC-045) |
| `--difficulty TIER` | nothing; **no `choices=`** | `difficulty.parse_tier` → `UnsupportedDifficulty` (AC-021) |
| `--export FORMAT` | `choices=list(export.FORMATS)` | the registry itself (see below) |
| `--mode` | `choices=["random","library","image"]` | mirrored by hand |

`--difficulty` is the one where it would be easy to get wrong, and `cli.py:299`
says so: the tiers *are* a closed set, so argparse could enforce them — but AC-021
asks for an unsupported tier to be a domain error with exit code 3. The names are
still read from `difficulty.Tier`, "so `--help` cannot drift from what `parse_tier`
accepts; **what is read is the vocabulary, not the rule.**"

`--export`'s `choices` come from `export.FORMATS` for the same reason in the other
direction, and `--mode` is the acknowledged exception: "sourcing's three modes do
not share a call signature, so there is no equivalent single table to read"
(`cli.py:343`).

`serve` carries **no `--host`** (`cli.py:388`): "the bind address is a constant in
`nonogram.web`, not an option, because **NFR-003/AC-052 is a property of the code
and must not become a property of how it was invoked.**" `--port 99999` is refused
by the socket layer, not the domain — and `_run_serve`'s `except` clause catches
`OSError` **and `OverflowError`**, because CPython's socket layer raises the latter
for a port outside 0..65535 (`cli.py:528`). Neither becomes a `NonogramError`:
"'this port is taken' is not a fact about puzzles, so the domain error hierarchy is
not widened to carry it."

### The exit-code table, grouped by remedy

`_EXIT_CODES` (`cli.py:72`) lives in the adapter and nowhere else, "so nothing
inward of COMP-001 needs to know a process exit code exists". `ExitCode` is
grouped **by what the user has to do**, not one code per class:

| Code | Name | Group |
|---|---|---|
| 0 | `OK` | |
| 1 | `INTERNAL_ERROR` | a mapping gap — i.e. a bug |
| 2 | `USAGE` | argparse's own `SystemExit(2)`; listed for completeness only |
| 3 | `INVALID_INPUT` | go and change what you passed in |
| 4 | `GENERATION_FAILED` | the run did not produce a usable puzzle; try again |
| 5 | `EXPORT_REJECTED` | INV-002 refused, or the write failed |

`exit_code_for` (`:112`) walks the error's MRO, so a subclass inherits its group.
Two later errors needed no new row: `SizeTooSmallForSource` finds `INVALID_INPUT`
through `SizeOutOfRange`, and `GivenCellsCapExceeded` finds `GENERATION_FAILED`
through `GenerationAbandoned`.

Two rows exist for errors **no CLI path raises** — `NotUniquelySolvable` and
`UnletterableTitle`, both from the admin panel — and the comments say why they are
listed anyway (`:101`, `:91`): "every declared domain error must be grouped, and
`INTERNAL_ERROR` is reserved for a mapping gap."

## COMP-008 — the web UI

### The bind is a constant, and that is the whole access control

```python
LOOPBACK_HOST = "127.0.0.1"          # web/server.py:35
DEFAULT_PORT  = 8765                 # :41
class LoopbackHTTPServer(ThreadingHTTPServer): ...   # :44
return LoopbackHTTPServer((LOOPBACK_HOST, port), WebUIRequestHandler)   # :84
```

`server.py:8` records that a module constant with no parameter, env var or kwarg
override is a *required consequence* of ADR-0020 rather than a framework default:
"a default can change under you between releases, and a default is not checkable."
`--port 0` asks the kernel for any free port, which is how the tests bind without
racing each other.

**Threading is not about concurrency.** `server.py:17`: BCON-0001 forbids a second
user and ADR-0021 relies on exactly one generation in flight; threading exists so
a browser's second connection (favicon, reload) does not deadlock behind a
30-second generation.

`create_server` / `serve_on` is a deliberate two-call split (`:67`, `:87`) so
`cli._run_serve`'s `except` covers **the bind and nothing else**, and so a test can
drive a real socket without owning a blocking loop — "which is what lets AC-052
check the bound interface behaviourally rather than by reading back a constructor
argument."

`serve_on` swallows `KeyboardInterrupt` so `nonogram serve` exits 0, and
`server_close()`s in a `finally`. **In-flight requests are not awaited**: handlers
are daemon threads and `socketserver`'s join tracks only non-daemon ones, so a
generation still running is abandoned — "the same accepted outcome ADR-0021 already
records for a browser that times out first" (`:107`).

### Routing

```python
ROUTES = {                                        # web/handler.py:927
    ("GET",  "/"):                WebUIRequestHandler._serve_form,
    ("POST", pages.FORM_ACTION):  WebUIRequestHandler._generate,
}
```

Keyed on the same `pages.FORM_ACTION` (`pages.py:102` = `"/generate"`) the form's
`action` renders from, "so the two cannot disagree about where a submission goes."

**Two further routes are prefix-matched in `_dispatch` and never appear in that
table**: `GET /upload/<token>` (`:846`, CARD-037) and `GET /static/<file>`
(`:578`, CARD-034). The honest route count is four.

Dispatch order (`:402`): conflicting `Host` → 400; non-local `Host` → 400;
`_cross_origin_refusal()` → 400; then the two prefixes, then `ROUTES`, then 404 as
`text/plain` with `nosniff`. *Every* `Host` value is read (`get_all`), not the
first — RFC 7230 §5.4 forbids more than one and two that disagree have no single
answer. A request with **no** `Host` is served on every protocol version, because
`Host` is a forbidden header name to `fetch`/XHR so a missing one is never the
attacker's shape, and refusing it would break `curl --http1.0` and the module's own
AC-052 probes.

Two transport bounds, both framed as transport and not domain (ADR-0019/R1):

- `IDLE_TIMEOUT_S = 30` (`:77`), applied as the handler's `timeout` class
  attribute so `StreamRequestHandler.setup` turns it into a socket `settimeout`.
  "The only thing being bounded is *silence*."
- `MAX_BODY_BYTES = 64 * 1024` (`:89`). The form's own body is a few hundred bytes,
  so this is two orders of magnitude of headroom, and what it actually bounds "is a
  body nobody typed: `Content-Length: 4000000000` on a loopback socket would
  otherwise be read into memory in full, because `http.server` bounds request
  *lines* and header counts and nothing else." Over the cap → 413, but only after
  reading `min(declared, MAX_BODY_BYTES)` so the refusal is drained enough to be
  delivered rather than arriving as a reset.

`protocol_version` stays at `HTTP/1.0` (`:242`), so every connection closes after
one response: this handler reads a body on exactly one route, and "persistent
connection + unread body is how a server desynchronises and starts answering
leftovers as the next request."

### Cross-origin refusal: why loopback is not enough

This is the part of COMP-008 most easily misread as redundant, and
`handler.py:283` states the attack plainly: a browser sets `Host` from the
request's *target*, so a form on `https://evil.example.com` posting to
`http://127.0.0.1:8765/generate` arrives with an allowlisted `Host` over a loopback
socket and — on the bind and the `Host` check alone — **is served**. Since
`POST /generate` exists, "served" means the pipeline runs and writes files at a
path the attacking page chose. The attack needs no reply, so same-origin policy and
CORS never come into it.

`_cross_origin_refusal` (`:282`) therefore reads three signals, in order:

```python
target = urllib.parse.urlsplit(self.path).netloc
if target and not _host_is_local(target):           return f"unrecognised request-target authority: {target}"
for site in self.headers.get_all("Sec-Fetch-Site") or []:
    if site.strip() not in ALLOWED_FETCH_SITES:     return f"cross-site request: {site.strip()}"
for origin in self.headers.get_all("Origin") or []:
    if not _origin_is_local(origin):                return f"foreign origin: {origin.strip()}"
return None
```

- `ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})` (`:107`) — **one**
  allowlist serving all three checks, deliberately, "so they cannot drift into
  three notions of 'local'."
- `ALLOWED_FETCH_SITES = frozenset({"same-origin", "none"})` (`:122`), compared
  exactly after `.strip()` and nothing else. The two spec values it omits —
  `same-site` and `cross-site` — "both say the request was started by a document
  this server did not serve, which is the whole of the attack." The accepted set
  being two literals wide is what makes EC-004's "for any such input" checkable.
- `Sec-Fetch-Site` and `Origin` are chosen because page script can neither forge
  nor suppress them. **`Referer` is deliberately not consulted** (`:331`):
  suppressible by a referrer policy the attacking page controls, "so a rule resting
  on it would be one the attacker can switch off."
- A request carrying **none** of the three is served (AC-058) — `curl`, a typed
  URL. `:319` is careful that "cannot be *suppressed*" would be too strong for
  `Origin`, and explains why absence is safe rather than lucky: the Fetch standard
  requires `Origin` on every cross-origin non-`GET`/`HEAD` request, `<form
  method=post>` included, and the only route that writes files is `POST /generate`.
- `_port_is_well_formed` (`:125`) exists because `urlsplit` reads `127.0.0.1:` and
  `127.0.0.1:notaport` as the *host* `127.0.0.1`.

A recorded scope limit (`:336`): a method with no `do_*` is answered **501 by
`BaseHTTPRequestHandler` before `_dispatch` runs** — measured on the wire with
cross-site headers attached and nothing written. EC-004's "never routes it to a
handler" holds by that different mechanism, so NFR-004's literal 400 "is a
statement about the two routed methods." The overridden `send_error` (`:487`) makes
that 501 `text/plain` with `nosniff`, echoing nothing off the wire.

### The submission path, and why every failure is HTTP 200

`_generate` (`:663`) reads the body, branches on media type
(`multipart/form-data` → `multipart.read`; **everything else, including no
`Content-Type`** → `submission.read(raw.decode("utf-8", "replace"))`), resolves a
retained upload token if one was posted, then makes **the same two calls
`cli._run_generate` makes, in the same order, sharing one `try`**.

That shared `try` is EC-003's whole mechanism: the exception becomes a page
*before* `_respond` is called, so success and failure are the same single write and
a half-written success can never be followed by an error.

Three caught arms, all **200**:

- `posted.request is None` → "The form could not be read.", refused before the
  orchestrator runs;
- `except NonogramError` — caught at the hierarchy base, not class by class, "so an
  error a later card adds is reported by this code without being edited into it".
  `UnreadableImage` additionally releases the retained upload, since a file that
  cannot be decoded fails identically however often it is resubmitted;
- `except OSError` → "A file for this request could not be read or written." This
  arm is **deliberately wider than the CLI's**, and `:713` records why: widening it
  in the CLI once reported a missing picture as "export rejected", so the web
  wording must be true of either call and names neither.

Anything else is **not** caught — stack trace on stderr, dropped connection. "A
blanket `except` here would turn a bug in this package into a tidy page claiming
the run was merely refused."

`handler.py:886` gives the 200-on-failure decision outright: **"Sorting domain
outcomes into HTTP status families would be a second error taxonomy beside
`cli.exit_code_for`'s exit-code table — the adapter drift ADR-0019 names as the
accepted cost of two adapters."** The package has **no table of error classes at
all**; it shows the error's own `str()`, the same text `cli._report` prints. The
only non-200s it emits are 400, 404, 413 and the stdlib's 501. Cleanup is a
`finally` (`:838`): "a bug three lines from here must not leak the file the same way
it must not corrupt the response."

### Multipart is hand-rolled because the baseline is closed

`cgi.FieldStorage` was removed in Python 3.13 (PEP 594) and the floor is 3.14, so
there is **no stdlib multipart parser**. ADR-0020's answer is
`email.parser.BytesParser` over reconstructed headers-plus-body
(`web/multipart.py:1`).

The sharp edge was found **by measurement, not from the docs** (`:10`):
`get_payload()` without `decode=True` re-encodes through the declared charset
(`ascii` when none) with `errors="replace"`, "so every byte 0x80–0xFF silently
becomes `U+FFFD`"; `get_payload(decode=True)` re-encodes with `surrogateescape`,
the exact inverse, and is used for **every** part, text as well as image.
`CARD-021`'s notes call it "verified empirically (not assumed from the docs) to be
the one accessor that survives a payload containing every byte value 0-255 and the
boundary sequence itself."

### Retention tokens, and the design that was rejected

`web/uploads.py:6` quotes the rejected version verbatim from an abandoned branch
kept as a patch file at `meta/ops/CARD-037-uncommitted-work-20260921.patch`:

```python
persisted_path = Path(fields["persisted_image_path"][0])
```

— which accepts a filesystem path from the client and opens it as the picture:
"any readable image on the server becomes a puzzle, and for anything else the
response still distinguishes 'exists' from 'does not'."

So the browser gets an opaque `secrets.token_urlsafe(24)` (`:70`), held in a
module-level `OrderedDict` (`:59`) bounded by **count, not time**:
`MAX_RETAINED = 8` (`:55`), evicting oldest-first and unlinking, "because a clock
would need a sweeper to run somewhere, and this server has no scheduler."
`resolve` (`:78`) returns `None` for a non-`str`, an empty string, an unminted
token, and a token whose file has vanished — "so a submitted path is simply a
string nobody minted."

### `pages.py`: no template engine, and a latent regex hazard

CON-008 scopes the UI to one form page, one POST endpoint and one result page —
below the threshold where a template language pays for itself, "and ADR-0006's
dependency baseline is closed anyway" (`pages.py:1`). `FORM_PAGE` is an f-string
built once at import.

The escaping rule is **asserted, not remembered**:
`TestWebPages_EscapingRuleIsTheOneTheDocstringStates`
(`tests/test_web_server.py:2416`) walks `pages.py`'s AST and fails on any
unescaped interpolation absent from `_UNESCAPED_PAGE_INTERPOLATIONS`, mapping each
exemption to the *kind* the docstring says it is. A further test (`:2518`) regexes
the docstring itself and asserts its numbers equal the walk — as shipped,
`pages.py:26` states 53 interpolations, 16 escaped, 37 unescaped — so "a docstring
reworded from memory fails here rather than at the next review."

**The hazard worth knowing before editing the CSS.**
`tests/test_web_server.py:1937`:

```python
def _form_field_names() -> set[str]:
    """Every ``name="..."`` in the form page — the fields a submission posts."""
    return set(re.findall(r'name="([^"]+)"', pages.FORM_PAGE))
```

That regex runs over the **whole rendered page**, which by construction contains
the entire `_STYLE` CSS block (interpolated at `pages.py:451`) and the inline
`<script>` that follows it. Its consumer,
`test_the_form_offers_the_same_option_surface_as_the_cli` (`:1942`), ends in two
**exact set equalities** against `cli.build_parser()`'s destinations:

```python
assert argv_options - form_options == {"extent", "mode", "density", "library_key"}
assert form_options - argv_options == {"size"}
```

So any `name="…"` literal anywhere in the CSS or JS — a `[name="x"]` attribute
selector, a `querySelector('[name="x"]')`, an inline SVG attribute — is harvested
as a form field and **both equalities break at once**. Because the running-server
fixture and the full-page assertions are shared across the module, one CSS edit
cascades into dozens of failures with no mention of CSS in any message. As shipped
it is clean: grepping all of `_STYLE` (`pages.py:160`-`445`) for `name="` returns
zero matches, and the seven in the form body are the real controls. The hazard is
latent and structural — the test asserts on rendered HTML rather than on a declared
field list.

### The shipped form is image-mode only

CARD-032 removed the source dropdown and the mode-specific fields
(`pages.py:441`). The rendered controls are `image`, `size`, `difficulty`, `name`,
`seed`, `out`, `export_formats` — **no `mode`, no `density`, no `library_key`** —
and the two set equalities above are how that gap is pinned rather than described.
The urlencoded path still accepts all three modes (a guardrail kept that path
unchanged), so CMD-001 and CMD-002 are reachable through `web` only by a
hand-written body, never from the form.

`web/submission.py` is as thin as `cli._run_generate`'s request-assembly block and
**decides nothing about the values** (ADR-0019/R1): `size=60` produces a request
carrying 60 and earns the same domain error `--size 60` does, "which is what makes
the two adapters tell one story by construction instead of by parallel
maintenance." Six documented behaviours: *blank means absent* (`parse_qs` drops
empty values, exactly how a browser spells "flag not passed", so an untouched
`name` box is `None` → FR-015 auto-naming, while `name=%20` travels inward and
earns `InvalidPuzzleName`); `_NUMERIC_FIELDS = ("density", "seed")` as the web
spelling of argparse's `type=int`; `_extent_token` accepting `N` or `NxM` and
nothing else; **two** value-shaped checks only, `mode` against `pages.MODES` and
format against `export.FORMATS`, "because the domain put them here" — without them
a hand-written `export_formats=png&bogus` would write the PNG and *then* fail, a
partial export; no NUL in any field; and a `Submission` where exactly one of
`request`/`unreadable` is meaningful.

`submission._EXTENT_SEPARATOR` (`:134`) is a byte-for-byte duplicate of
`cli._EXTENT_SEPARATOR` rather than an import, cross-checked from the test tree —
the **second** instance of the reimplement-and-cross-check pattern after
`solver.mask_runs`, and its docstring names that precedent.

## COMP-009 — the admin panel's door

Two **mutually exclusive** modes, chosen once at boot by one env var.

```python
REMOTE_HOST_VAR = "ADMIN_ALLOWED_HOST"       # admin/app.py:453
ADMIN_USER_VAR / ADMIN_PASSWORD_VAR          # :457
DEFAULT_ADMIN_USER = "admin"                 # :459
MIN_ADMIN_PASSWORD_LENGTH = 16               # :481
DEV_SECRET_KEY = "dev-key-change-in-production"   # :469
LOOPBACK_HOST = "127.0.0.1"                  # :377
DEFAULT_PORT = 5000                          # :381
```

`LOOPBACK_HOST` is a module constant and `main(port=DEFAULT_PORT)` takes a port and
nothing else, for the same reason `web.create_server` does (`:6316`): a `host=`
parameter "would move NFR-003's criterion out of this module and into every call
site."

The env var is read **once**, at `create_app` (`:1234`), deliberately: "an admin
whose reachability could change under a running process would be a configuration
question with no single answer, and the boot-time refusal below only means anything
if this is the value the hook will use."

### Fail closed at boot, in the build log

Three refusals, all gated on `ADMIN_ALLOWED_HOST` being set, raising
`AdminConfigurationError(RuntimeError)` (`:499`) **before a socket exists**:

1. no `ADMIN_PASSWORD` (`:1244`);
2. a password under 16 characters, with the generator one-liner in the message
   (`:1254`);
3. `SECRET_KEY` still the dev literal (`:1264`), "because cookies signed with it
   can be forged by anyone who has read the source".

On success it also raises `SESSION_COOKIE_SECURE` to `True` (`:1274`), which is
`False` by default (`:1227`).

And `REGRADE_ENABLED = not remote_host` (`:1283`): **the deployed panel does not
offer the re-grade at all.** Both routes `abort(404)` and the nav hides it, because
it "rewrites every stored grade with no undo … not a button on a panel the internet
can reach."

### The request hook replaces the local rule

`_refuse_what_this_panel_should_not_serve` (`:1302`) is a `before_request` hook:

- **Local mode** (`ADMIN_ALLOWED_HOST` unset): `_host_is_local(Host)` must be true,
  else a rendered **404**. Nothing else is asked.
- **Deployed mode**, in order:
  1. `_host_is_the_configured_remote` — a plain **equality** on the parsed hostname
     (`:589`), not an allowlist. Failure → bare 404 to the caller, and
     `app.logger.warning("refused: Host %r does not match %s=%r", …)` to the
     operator (`:1350`), "because the one refusal designed to be indistinguishable
     from 'no such page' is also the one they have to debug blind."
  2. `_credential_is_correct` → **401** with
     `WWW-Authenticate: Basic realm="Nonogram admin", charset="UTF-8"` (`:768`).
  3. `_request_is_cross_site` → **403** `text/plain`, "Refused: this request was
     started by another site." (`:753`) — explicitly not a 404 ("this caller
     reached the configured host *and* presented the credential") and not a 401
     ("re-prompting would invite the operator to re-enter it in answer to a page
     they did not open").

**`Host: localhost` is refused in deployed mode even with the right credential**,
and `:1326` is the load-bearing clause: behind a reverse proxy `REMOTE_ADDR` is the
proxy — "Render's logs report every request as `127.0.0.1`" — so leaving the
loopback door open would make `Host: localhost` a password bypass. The two doors
are "mutually exclusive by construction and not by vigilance."

Mechanism details that matter when touching this code:

- `_credential_is_correct` (`:603`) computes **both** `hmac.compare_digest` results
  before the `and`, "so a wrong username therefore costs the same work as a wrong
  password", and compares **UTF-8 bytes** because `compare_digest` raises
  `TypeError` on non-ASCII `str` — "an availability bug reachable by anyone who can
  type a non-ASCII character into a login box."
- `_host_is_local` (`:393`) refuses `@`, `/`, `#`, `?` **before** `urlsplit`,
  because `urlsplit` reads `evil.com:80@127.0.0.1` as host `127.0.0.1` — "which is
  how the first version of this function let that value through, until
  `tests/test_admin_binding.py` said so."
- `_request_is_cross_site` (`:687`) reads every value of `Sec-Fetch-Site` and
  `Origin` by **splitting on commas**, not just iterating `get_all`, because WSGI
  folds repeated headers into one comma-joined value. Measured: "a mutation
  restricting that loop to its first element changed nothing, because there was
  never a second (CARD-085 review, M7)."
- `_is_top_level_navigation` (`:653`) is the one carve-out: a cross-site **GET/HEAD**
  with `Sec-Fetch-Mode: navigate` and `Sec-Fetch-Dest: document`. The method test
  is load-bearing — without it the exemption re-opens CSRF.
- `add_headers` (`:1382`) drops `Access-Control-Allow-Origin: *` in deployed mode
  only, keeping `X-Content-Type-Options: nosniff` and `X-Frame-Options: SAMEORIGIN`
  always.
- `admin/app.py:390`'s `ALLOWED_HOSTS` is a **deliberate reimplementation** of
  `web/handler.py`'s identical frozenset (`:385` cites ADR-0007 and names
  `mask_runs` as the precedent): "Two short allowlists that agree is the intended
  shape; one importing the other is not."

### The test suite maps one-to-one onto that design

`tests/test_admin_auth.py` has seven classes —
`TestAdminAuth_LocalModeIsUnchanged` (`:82`),
`_DeployedModeRequiresACredential` (`:117`),
`_DeployedModeHasNoLoopbackBypass` (`:196`),
`_RefusesToBootMisconfigured` (`:269`),
`_EveryRouteIsBehindTheCredential` (`:354`),
`_ComparesBothHalvesWithoutShortCircuit` (`:499`),
`_RefusesRequestsAnotherSiteStarted` (`:570`).

Three are worth naming for what they pin rather than what they test:
`test_a_wrong_credential_never_reaches_the_database` (`:166`) holds the "a refusal
never costs a database query" claim at `app.py:1335`;
`test_no_route_is_reachable_without_the_credential` (`:455`) sweeps the router and
is itself guarded by `test_the_sweep_builds_urls_the_router_actually_matches`
(`:406`); `test_the_gateway_folds_repeats_which_is_why_splitting_is_the_check`
(`:684`) pins the comma-splitting above.

`CARD-085.md`'s worktree notes carry a measured diagnosis an operator can reuse:
with `DATABASE_URL` pointed at a black-holed address, a request carrying the Render
`Host` came back 404 in **6.9 ms** while the same request carrying
`Host: localhost` took **75 seconds** and raised `OperationalError`. "That gap is
the whole proof that the 404s were the guard and not the database."

## Bounds and honest gaps

- **CON-017's "no state beyond the export files" is too strong for COMP-008 as
  literally stated** — the claim appears in the component diagram and at
  `web/__init__.py:73`. In code: `web/uploads.py:59` is a module-level,
  process-lifetime `OrderedDict` of tokens → temp files (`MAX_RETAINED = 8`);
  `web/multipart.py:104` writes via `tempfile.mkstemp`, outside `--out`;
  `GET /upload/<token>` reads those bytes back off disk; `GET /static/<file>`
  serves from `web/static/`. The *spirit* survives — nothing persists across runs
  by design — but the sentence does not. `uploads.clear()` (`:107`) exists "for
  tests, and for a caller that wants the store empty; the server has no shutdown
  hook of its own to call it from", so **nothing clears the store on Ctrl-C** and
  up to 8 temp files are left for the OS to reap.
- **`WebUIRequestHandler`'s own docstring says nothing is served from disk.**
  `handler.py:236`: "nothing in this UI is served from disk — the form is a string
  constant (ADR-0020). Inheriting from [`SimpleHTTPRequestHandler`] would put the
  whole working directory one path-traversal bug away from a browser, **to serve
  zero files**." Two routes now serve from disk, and `_serve_static` (`:578`)
  carries hand-written path-traversal defence (`".." in path or
  path.startswith("/")`, then `.resolve()` + `relative_to(base_dir)`) to prove it.
  CARD-034 added the route without updating the docstring the class leads with.
- **ADR-0020's Decision text does not cover the static route or client-side
  JavaScript**, both of which ship (`web/static/metadata.js`, 380 lines; the inline
  `<script>` at `pages.py:452`). Not a CON-008 violation: CON-008 forbids an
  in-browser preview of the **generated puzzle**, while `metadata.js` previews the
  **uploaded source**. Different artifact — but the ADR is behind the code.
- **Dead code inside the shipped web adapter.** `WebUIRequestHandler._fail`
  (`handler.py:880`) has no call site — every failure goes through `_fail_inline`
  (CARD-030) — and it is the sole caller of `pages.failure_page`, so that is dead
  too. `pages.result_page` likewise has no production caller. Both
  `pages.py`'s docstring and `web/__init__.py:49` still describe a three-page
  design that CARD-030 collapsed into one.
- **`web/metadata.py` (140 lines) has no production caller.** Its only importers
  are two test files. CARD-034's notes record both history and intent: "CARD-031's
  server-side rendering had zero call sites from the day it was written, and
  CARD-104 deleted it. A browser without the File API gets no metadata, before and
  after." What ships is `web/static/metadata.js`, driven from
  `pages.py:515`. **Not determinable from code** whether the module is retained
  deliberately or simply unremoved.
- **`web/__init__.py:13` claims the package imports `sourcing` "to provide
  image/random/library input modes to the form."** The only importer is
  `metadata.py:16`, which has no production caller, and the form offers one mode.
  The dependency is real in the AST and vacuous at runtime.
- **`submission.DEFAULT_MODE`'s docstring is false.** `submission.py:112` says the
  default "mirror[s] `cli.build_parser`'s `--mode` default rather than inventing a
  second one" — then sets `DEFAULT_MODE = "image"`, while `cli.py:240` is
  `default="random"`. CARD-032 changed one side and the comment still claims they
  agree. A reader trusting the sentence would conclude a bodiless POST generates a
  random grid.
- **Three ways the admin socket can be opened, and they disagree.**
  `python -m nonogram.admin.app` → loopback, port 5000. `start.sh` →
  `gunicorn --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-1} --timeout 120
  --graceful-timeout 30 … "nonogram.admin.app:create_app()"`. `Procfile` →
  `flask --app src.nonogram.admin.app run --host=0.0.0.0 --port=$PORT`, i.e.
  **Flask's dev server, every interface, and the `src.` prefix `start.sh`
  documents at length as a trap** (it imports the package a second time under a
  second name, producing two distinct `LongestSideBucket` enums and killing Print
  setup with `ValueError: tuple.index(x): x not in tuple` on any book whose plan is
  stored — "A plan-less book renders fine, which is what made it look like bad data
  in production"). **Not determinable from code which one production runs**:
  `render.yaml` declares itself non-authoritative on its own first line, and
  `docs/deploy/render.md` marks each field `TODO(owner)`, recording only that as
  last observed on 2026-09-23 it was the `flask run` / `src.` shape.

## Related

- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) — the rank table and `_LAUNCH_EDGE`
- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) · [08-playing-a-stored-puzzle.md](08-playing-a-stored-puzzle.md)
- ADRs: [ADR-0008](../../../../meta/architecture/decisions/adr/0008-packaging-and-runtime.md) · [ADR-0010](../../../../meta/architecture/decisions/adr/0010-cli-argument-parsing.md) · [ADR-0019](../../../../meta/architecture/decisions/adr/0019-web-ui-component-boundary.md) · [ADR-0020](../../../../meta/architecture/decisions/adr/0020-web-ui-http-layer.md) · [ADR-0021](../../../../meta/architecture/decisions/adr/0021-web-ui-request-handling.md) · [ADR-0030](../../../../meta/architecture/decisions/adr/0030-admin-remote-access-behind-a-credential.md)
- Cards: `CARD-019`/`CARD-020` (the web adapter and the cross-origin check) · `CARD-021` (hand-rolled multipart) · `CARD-032` (image-only form) · `CARD-037` (retention tokens) · `CARD-085` (the credentialed door)
