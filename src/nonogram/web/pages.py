"""The web UI's HTML, as string constants (ADR-0020, CON-008).

No templating engine, and none coming: CON-008 scopes the whole UI to one form
page, one POST endpoint and one result page, which is below the threshold where
a template language pays for itself — and ADR-0006's dependency baseline is
closed anyway (guardrail G-6). :data:`FORM_PAGE` is built once, at import, and
is a plain ``str`` from then on.

Three of the form's option lists are read from the domain rather than spelled
out here — the export formats from ``export.FORMATS`` and the difficulty tiers
from ``difficulty.Tier`` — which is the same move ``cli.py`` already makes for
``--export``'s ``choices`` and ``--difficulty``'s help text. What is read is
*vocabulary*, not a rule: a value this page did not offer still parses, still
travels inward, and is still rejected by the domain (guardrail G-4). The
alternative — a second hand-maintained copy of both lists — is precisely the
adapter drift ADR-0019 names as an accepted cost of having two adapters, and
there is no reason to pay it where a registry already exists to read.

The sourcing modes are the exception, spelled out below exactly as ``cli.py``
spells them out in its ``--mode`` ``choices``: COMP-003's three modes do not
share a call signature, so there is no single table to read for them.
"""

from __future__ import annotations

import html

from nonogram import difficulty, export

__all__ = ["FORM_ACTION", "FORM_PAGE"]

#: Where the form posts. CARD-020 routes it; until then a submission gets a
#: ``501`` (guardrail G-5) — the status is the standard library's, since there
#: is no ``do_POST``, but the response is written by
#: :meth:`nonogram.web.handler.WebUIRequestHandler.send_error` and reads
#: ``501 Not Implemented``. The path is named here rather than inlined so that
#: card adds its route against a constant this page already agrees with.
FORM_ACTION = "/generate"

#: ``--mode``'s three values, mirrored by hand from ``cli.py`` for the reason
#: given in the module docstring.
_MODES: tuple[str, ...] = ("random", "library", "image")


def _options(values: tuple[str, ...] | list[str], *, blank: str | None = None) -> str:
    """Render ``<option>`` tags, optionally led by an empty "unset" choice.

    ``blank`` is what an *absent* CLI flag looks like on a form: the CLI's
    ``--difficulty`` may simply not be passed, and a ``<select>`` has no way to
    express "not passed" other than an empty-valued option. Selecting it posts
    an empty string, which CARD-020 maps back to ``None``.
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


#: The form page. Every field is named for the ``GenerationRequest`` field it
#: fills, so CARD-020's mapping is a lookup rather than a translation table.
#: Nothing here constrains a value: no ``min``/``max`` on ``size`` or
#: ``density``, no ``required`` — an out-of-range number must reach the domain
#: and be rejected there (AC-050, guardrail G-4), and an HTML validation
#: attribute would stop it in the browser instead, which is the same mistake as
#: putting ``choices=`` on ``--difficulty`` (ADR-0010).
FORM_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>nonogram</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 34rem; }}
label {{ display: block; margin: 0.75rem 0; }}
span {{ display: block; font-weight: 600; }}
small {{ color: #555; font-weight: 400; }}
input, select {{ width: 100%; padding: 0.3rem; box-sizing: border-box; }}
fieldset {{ border: 1px solid #ccc; margin: 0.75rem 0; }}
fieldset label {{ display: inline-block; margin-right: 1rem; width: auto; }}
fieldset input {{ width: auto; }}
button {{ margin-top: 1rem; padding: 0.5rem 1.5rem; font-size: 1rem; }}
</style>
</head>
<body>
<h1>nonogram</h1>
<p>Generate a uniquely-solvable black-and-white nonogram. The same options the
<code>nonogram generate</code> command takes; the same pipeline behind them.</p>
<form method="post" action="{html.escape(FORM_ACTION)}">
  <label><span>Source</span>
    <select name="mode">
        {_options(_MODES)}
    </select>
  </label>
  <label><span>Library key <small>&mdash; for the library source</small></span>
    <input type="text" name="library_key">
  </label>
  <label><span>Size <small>&mdash; square grid edge length</small></span>
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
