"""The web UI's HTML: the form, the result page, the failure page (ADR-0020).

No templating engine, and none coming: CON-008 scopes the whole UI to one form
page, one POST endpoint and one result page, which is below the threshold where
a template language pays for itself — and ADR-0006's dependency baseline is
closed anyway. :data:`FORM_PAGE` is built once, at import, and is a plain
``str`` from then on; the two pages a submission produces are f-strings
assembled per response, because their content is the run's.

Every **string** that came off the wire goes through :func:`html.escape` at the
point it is interpolated, and that is not belt-and-braces here: a result page
carries a puzzle name and file paths the user chose, and a failure page carries
a domain error's message, which quotes them back (an unknown library key, an
unusable name). The responses also travel with ``nosniff`` and a ``text/html``
content type from ``handler._respond``, so the escaping is the guard that
actually does the work rather than the second one. Values that are literals
today are escaped anyway (``failure_page``'s ``summary``), so no later caller
has to notice which is which.

The rule is stated over caller-supplied *strings* because most interpolations
here are not that, and the split is asserted rather than remembered:
``TestWebPages_EscapingRuleIsTheOneTheDocstringStates`` in
``tests/test_web_server.py`` walks this module's AST and fails on any unescaped
interpolation whose expression is not one of the ones named below. As shipped
there are 23 f-string interpolations, of which 11 call :func:`html.escape` at
the point of interpolation. The other 12 are each one of four kinds:

* **4 module constants** — ``_STYLE`` (twice), ``SUCCESS``, ``FAILURE``;
* **5 fragments built here**, by a function that escaped as it built them —
  :func:`_options` (twice), :func:`_checkboxes`, :func:`result_page`'s
  ``written``, :func:`failure_page`'s ``listed``;
* **:func:`_shell`'s two parameters** — ``title``, which its own docstring
  binds to be a literal, and ``body``, which the caller has already escaped;
* **one value off the wire**: :func:`result_page`'s ``{seed:d}``. It is the
  single exception to the sentence above, and it is safe not because it is
  escaped but because it is not a string — the ``:d`` format spec admits an int
  and nothing else, so a later caller passing markup there raises instead of
  emitting it.

Neither page renders the puzzle (CON-008, guardrail G-4). What a successful run
reports is the puzzle's name, the seed and the files written; :func:`result_page`
states how that differs from what ``cli._run_generate`` prints for the same run,
and why.

Two of the form's option lists are read from the domain rather than spelled out
here — the export formats from ``export.FORMATS`` and the difficulty tiers from
``difficulty.Tier`` — which is the same move ``cli.py`` already makes for
``--export``'s ``choices`` and ``--difficulty``'s help text. What is read is
*vocabulary*, not a rule: an unoffered *difficulty* still parses, still travels
inward, and is still rejected by the domain (ADR-0019/R1, guardrail G-2). An
unoffered *export format* is the one exception, and it is the domain's own
instruction rather than this package's judgement — ``export.for_format``
refuses one with a bare ``ValueError`` and documents the adapter as the place
that rejects it, exactly as ``sourcing.for_mode`` does for a mode (see
:mod:`nonogram.web.submission`). The alternative to reading the registries — a
second hand-maintained copy of both lists — is precisely the adapter drift
ADR-0019 names as an accepted cost of having two adapters, and there is no
reason to pay it where a registry already exists to read.

The sourcing modes are the exception, spelled out below exactly as ``cli.py``
spells them out in its ``--mode`` ``choices``: COMP-003's three modes do not
share a call signature, so there is no single table to read for them.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

from nonogram import difficulty, export

__all__ = [
    "FAILURE",
    "FORM_ACTION",
    "FORM_PAGE",
    "MODES",
    "SUCCESS",
    "failure_page",
    "result_page",
]

#: Where the form posts, and the path ``handler.ROUTES`` registers
#: ``do_POST``'s route under. Named here rather than inlined in both places so
#: the form and the router cannot disagree about it.
FORM_ACTION = "/generate"

#: ``--mode``'s three values, mirrored by hand from ``cli.py`` for the reason
#: given in the module docstring. Public because it is not only the form's
#: option list: ``submission.read`` checks a posted ``mode`` against it, so the
#: set the form offers and the set the mapping accepts are one object.
MODES: tuple[str, ...] = ("random", "library", "image")


def _options(values: tuple[str, ...] | list[str], *, blank: str | None = None) -> str:
    """Render ``<option>`` tags, optionally led by an empty "unset" choice.

    ``blank`` is what an *absent* CLI flag looks like on a form: the CLI's
    ``--difficulty`` may simply not be passed, and a ``<select>`` has no way to
    express "not passed" other than an empty-valued option. Selecting it posts
    an empty string, which ``urllib.parse.parse_qs`` drops from the parsed
    fields, so the request is built with no tier at all — see
    :mod:`nonogram.web.submission`.
    """
    tags = [] if blank is None else [f'<option value="">{html.escape(blank)}</option>']
    tags += [f'<option value="{html.escape(v)}">{html.escape(v)}</option>' for v in values]
    return "\n        ".join(tags)


def _checkboxes(name: str, values: tuple[str, ...]) -> str:
    """Render one checkbox per value — the form's answer to a repeatable flag.

    ``--export`` is ``action="append"`` on the CLI; the HTML equivalent of a
    flag repeated is several controls sharing one name, which is why every box
    below is named ``export_formats``.
    """
    return "\n    ".join(
        f'<label><input type="checkbox" name="{html.escape(name)}" '
        f'value="{html.escape(v)}"> {html.escape(v)}</label>'
        for v in values
    )


#: The one stylesheet, shared by the form and by the two pages a submission
#: produces, so all three are visibly one application.
_STYLE = """
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 34rem; }
label { display: block; margin: 0.75rem 0; }
span { display: block; font-weight: 600; }
small { color: #555; font-weight: 400; }
input, select { width: 100%; padding: 0.3rem; box-sizing: border-box; }
fieldset { border: 1px solid #ccc; margin: 0.75rem 0; }
fieldset label { display: inline-block; margin-right: 1rem; width: auto; }
fieldset input { width: auto; }
button { margin-top: 1rem; padding: 0.5rem 1.5rem; font-size: 1rem; }
code { word-break: break-all; }
"""

#: The form page. Every field is named for the ``GenerationRequest`` field it
#: fills, so :func:`nonogram.web.submission.read` is a lookup rather than a
#: translation table — with one exception the field's own label states: ``size``
#: is one box and ``GenerationRequest`` carries two sides, so a bare N fills
#: ``width`` and leaves ``height`` for the domain to derive from the source's
#: shape, exactly as a bare ``--size N`` does (FR-023, ADR-0022/R4). The
#: ``WxH`` field is CARD-028's.
#:
#: Nothing here constrains a value: no ``min``/``max`` on ``size`` or
#: ``density``, no ``required`` — an out-of-range number must reach the domain
#: and be rejected there (AC-050, ADR-0019/R1, guardrail G-2), and an HTML
#: validation attribute would stop it in the browser instead, which is the same
#: mistake as putting ``choices=`` on ``--difficulty`` (ADR-0010).
FORM_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>nonogram</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>nonogram</h1>
<p>Generate a uniquely-solvable black-and-white nonogram. The same options the
<code>nonogram generate</code> command takes; the same pipeline behind them.</p>
<form method="post" action="{html.escape(FORM_ACTION)}">
  <label><span>Source</span>
    <select name="mode">
        {_options(MODES)}
    </select>
  </label>
  <label><span>Library key <small>&mdash; for the library source</small></span>
    <input type="text" name="library_key">
  </label>
  <label><span>Size <small>&mdash; the grid's longer side in cells; the other
    side follows the source's own shape (a square in random mode)</small></span>
    <input type="text" name="size" inputmode="numeric">
  </label>
  <label><span>Density <small>&mdash; percent of cells filled</small></span>
    <input type="text" name="density" inputmode="numeric">
  </label>
  <label><span>Difficulty</span>
    <select name="difficulty">
        {_options(list(difficulty.Tier), blank="(any)")}
    </select>
  </label>
  <label><span>Name <small>&mdash; shown on the printed page</small></span>
    <input type="text" name="name">
  </label>
  <label><span>Seed <small>&mdash; for a reproducible puzzle</small></span>
    <input type="text" name="seed" inputmode="numeric">
  </label>
  <fieldset>
    <legend>Export formats</legend>
    {_checkboxes("export_formats", export.FORMATS)}
  </fieldset>
  <label><span>Output directory <small>&mdash; defaults to the working directory</small></span>
    <input type="text" name="out">
  </label>
  <button type="submit">Generate</button>
</form>
</body>
</html>
"""


#: The value of the ``data-outcome`` attribute each of the two submission pages
#: carries on its ``<p>`` summary. One machine-readable word per outcome, so a
#: reader — a test, a person viewing source — can tell a success page from a
#: failure page without parsing prose that is free to be reworded.
SUCCESS = "success"
FAILURE = "failure"


def _shell(title: str, body: str) -> str:
    """Wrap ``body`` in the same document the form page is (ADR-0020).

    One shell for all three pages, so a submission's answer is visibly the same
    application as the form that produced it.

    Both of this function's parameters are interpolated unescaped, and each has
    its own reason. ``title`` is therefore never caller data: both call sites
    below pass a literal, and that is the whole of the rule for it. ``body`` is
    markup by construction — a caller that escaped it would ship the tags to
    the browser as text — so it is contractually pre-escaped: every string that
    came off the wire is escaped by the caller before it reaches here. Neither
    is the *only* unescaped interpolation in this module; the module docstring
    enumerates all twelve and says which kind each is.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{_STYLE}</style>
</head>
<body>
{body}
<p><a href="/">Generate another</a></p>
</body>
</html>
"""


def result_page(name: str | None, seed: int, paths: Sequence[Path]) -> str:
    """The page a completed run produces (AC-049).

    Reports three things: the puzzle's name, the seed, and every file
    ``orchestrator.export_puzzle`` wrote, in the order it wrote them. The
    puzzle itself is not rendered (CON-008, guardrail G-4).

    That is deliberately **not** the same set of lines ``cli._run_generate``
    prints for the same run, and the three differences are each a consequence
    of a page not being a console:

    * the **name** is shown here and is not printed there. A console run was
      typed by the person reading it and the auto-generated name (FR-015) is
      recoverable from the ``wrote`` paths; a page can be reloaded, shared or
      left open, so it says what it made.
    * the **seed** is shown unconditionally, where the CLI prints it only when
      it drew one itself (``if request.seed is None``). ADR-0015's requirement
      is that a drawn seed be reportable, and a page has no scrollback to look
      it up in later, so showing it always discharges that at no cost; the
      alternative is a page whose contents depend on a field the reader cannot
      see from it.
    * FR-014's **nudge count** is not reproduced, and cannot yet be non-zero
      on any run that reaches this page: the counter is advanced only by the
      ``mode == "image"`` branch of ``orchestrator.generate``, and an
      image-mode submission from this form carries no picture (CARD-021), so it
      fails inward and renders :func:`failure_page` instead. The line becomes
      owed the moment the upload control lands.

    A run that asked for no export format wrote no files, and the page says so
    rather than showing an empty list — the same distinction the CLI draws by
    printing no ``wrote`` lines at all.

    Args:
        name: The puzzle's FR-015 name, as the aggregate carries it — which is
            to say ``str | None``, matching ``orchestrator.Puzzle.name``'s own
            declaration rather than narrowing it here. ``None`` is not reachable
            from this adapter today (``orchestrator.generate`` resolves the name
            before it constructs the ``Puzzle``), but this function is called
            *after* ``export_puzzle`` has already written the files, and outside
            the ``try`` EC-003 rests on, so the day the aggregate exercises its
            declared option a ``str``-only signature would answer with a dropped
            connection and a traceback. Rendered as no name instead.
        seed: The run's seed, drawn or supplied. Interpolated with a ``:d``
            format spec, which is what makes it the one value off the wire that
            reaches the markup without ``html.escape``.
        paths: The files written, from ``export_puzzle``'s return value.

    Returns:
        One complete HTML document.
    """
    if paths:
        written = "<ul>\n" + "\n".join(
            f"  <li><code>{html.escape(str(path))}</code></li>" for path in paths
        ) + "\n</ul>"
    else:
        written = "<p>No export format was requested, so no file was written.</p>"
    return _shell(
        "nonogram — generated",
        f"""<h1>Generated</h1>
<p data-outcome="{SUCCESS}">Generated <strong>{html.escape(name or "")}</strong>.</p>
<p>seed: <code>{seed:d}</code></p>
{written}""",
    )


def failure_page(summary: str, reasons: Sequence[str]) -> str:
    """The structured failure page (EC-003, AC-050, AC-051).

    The adapter's whole answer to a request that did not produce a puzzle: a
    one-line summary and the reasons, escaped, in a document that is otherwise
    the form's. No traceback, no exception class hierarchy, no HTTP status
    family invented for the occasion — the response carrying this page is a
    ``200``, because the page *is* the report and delivering it succeeded.
    That is also the reason this function takes prose rather than an exception:
    grouping domain errors into kinds is what ``cli.exit_code_for`` does for
    exit codes, and a second grouping in this package is precisely the adapter
    drift ADR-0019 names. There is nothing here to drift.

    Args:
        summary: One sentence saying what did not happen. Every call site
            passes a literal, and it is escaped here anyway — one call, and the
            module's escaping rule then has exactly one exception rather than
            three (see :func:`_shell`).
        reasons: One line per reason, escaped here. For a domain failure that
            is the error's own message — the same text ``cli._report`` prints
            after ``nonogram: error:``.

    Returns:
        One complete HTML document.
    """
    listed = "\n".join(f"  <li>{html.escape(reason)}</li>" for reason in reasons)
    return _shell(
        "nonogram — not generated",
        f"""<h1>Not generated</h1>
<p data-outcome="{FAILURE}">{html.escape(summary)}</p>
<ul>
{listed}
</ul>""",
    )
