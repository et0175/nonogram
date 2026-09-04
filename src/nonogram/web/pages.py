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
there are 54 f-string interpolations, of which 22 call :func:`html.escape` at
the point of interpolation. The other 32 are each one of seven kinds:

* **4 module constants** — ``_STYLE`` (twice), ``SUCCESS``, ``FAILURE``;
* **8+ fragments built here**, by a function that escaped as it built them —
  :func:`_options` (twice), :func:`_checkboxes`, :func:`result_page`'s
  ``written``, :func:`failure_page`'s ``listed``, and CARD-030 additions in
  :func:`form_with_result`;
* **:func:`_shell`'s two parameters** — ``title``, which its own docstring
  binds to be a literal, and ``body``, which the caller has already escaped;
* **multiple values off the wire**: ``{seed:d}`` across multiple functions.
  Each is safe not because it is escaped but because it is not a string — the
  ``:d`` format spec admits an int and nothing else, so a later caller passing
  markup there raises instead of emitting it.
* **JSON data**: ``metadata_json`` (CARD-037 persisted image metadata) — embedded
  in a JSON script block where no HTML escaping is needed.
* **Status messages with conditional content**: ``persisted_status`` (CARD-037) —
  pre-built HTML string showing filename, safe because built from empty string or literal HTML.

Neither page renders the puzzle (CON-008, guardrail G-4). What a successful run
reports is the puzzle's name, the seed and the files written; :func:`result_page`
states how that differs from what ``cli._run_generate`` prints for the same run,
and why.

The form's ``enctype`` is ``multipart/form-data`` (CARD-021), which is what
makes an ``<input type="file">``'s *content* — not just its file name — travel
in the POST body at all; ``nonogram.web.multipart`` is the module that then
has to read that shape back apart. A browser sends every field this way once
it is set, mode-agnostic submissions included, which is why
``nonogram.web.submission.read`` — the urlencoded reader — is still exercised
in this codebase only by a request built by hand (a test, or ``curl``): G-3
keeps that path *working*, not necessarily reachable from this rendered form.

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
import json
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
    "form_with_result",
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


def _options(values: tuple[str, ...] | list[str], *, blank: str | None = None, selected: str = "") -> str:
    """Render ``<option>`` tags, optionally led by an empty "unset" choice.

    ``blank`` is what an *absent* CLI flag looks like on a form: the CLI's
    ``--difficulty`` may simply not be passed, and a ``<select>`` has no way to
    express "not passed" other than an empty-valued option. Selecting it posts
    an empty string, which ``urllib.parse.parse_qs`` drops from the parsed
    fields, so the request is built with no tier at all — see
    :mod:`nonogram.web.submission`.

    ``selected`` is the value to mark as selected (for CARD-030 form re-population).
    """
    tags = []
    if blank is not None:
        is_selected = selected == ""
        tags.append(
            f'<option value="" {"selected" if is_selected else ""}>{html.escape(blank)}</option>'
        )
    for v in values:
        is_selected = selected == str(v)
        tags.append(
            f'<option value="{html.escape(v)}" {"selected" if is_selected else ""}>{html.escape(v)}</option>'
        )
    return "\n        ".join(tags)


def _checkboxes(
    name: str, values: tuple[str, ...], checked: set[str] | None = None
) -> str:
    """Render one checkbox per value — the form's answer to a repeatable flag.

    ``--export`` is ``action="append"`` on the CLI; the HTML equivalent of a
    flag repeated is several controls sharing one name, which is why every box
    below is named ``export_formats``.

    ``checked`` is a set of values to mark as checked (for CARD-030 form re-population).
    """
    if checked is None:
        checked = set()
    return "\n    ".join(
        f'<label><input type="checkbox" name="{html.escape(name)}" '
        f'value="{html.escape(v)}" {"checked" if v in checked else ""}> {html.escape(v)}</label>'
        for v in values
    )


#: The one stylesheet, shared by the form and by the two pages a submission
#: produces, so all three are visibly one application. Includes dark mode support
#: via prefers-color-scheme (AC-133, CARD-033).
_STYLE = """
:root {
  --text-primary: #000;
  --text-secondary: #555;
  --bg-primary: #fff;
  --bg-secondary: #f5f5f5;
  --border-color: #ccc;
  --button-bg: #007bff;
  --button-hover: #0056b3;
  --button-alt-bg: #e8e8e8;
  --button-alt-hover: #d0d0d0;
}

@media (prefers-color-scheme: dark) {
  :root {
    --text-primary: #e0e0e0;
    --text-secondary: #999;
    --bg-primary: #1a1a1a;
    --bg-secondary: #2a2a2a;
    --border-color: #444;
    --button-bg: #0d6efd;
    --button-hover: #0b5ed7;
    --button-alt-bg: #3a3a3a;
    --button-alt-hover: #4a4a4a;
  }
}

body {
  font-family: system-ui, sans-serif;
  margin: 2rem auto;
  max-width: 34rem;
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

h1 {
  margin-top: 0;
  margin-bottom: 0.5rem;
}

p {
  line-height: 1.5;
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin: 1rem 0 0.5rem 0;
}

span {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

small {
  color: var(--text-secondary);
  font-weight: 400;
  display: block;
  font-size: 0.875rem;
}

input, select {
  width: 100%;
  padding: 0.5rem;
  box-sizing: border-box;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 1rem;
}

input:focus, select:focus {
  outline: none;
  border-color: var(--button-bg);
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 1.5rem;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-grid > div:nth-child(1) { grid-column: 1; grid-row: 1; }
.form-grid > div:nth-child(2) { grid-column: 2; grid-row: 1; }
.form-grid > div:nth-child(3) { grid-column: 1; grid-row: 2; }
.form-grid > div:nth-child(4) { grid-column: 2; grid-row: 2; }

.form-section {
  margin: 0;
  padding: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background-color: var(--bg-secondary);
}

.form-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}

.form-section > label:first-child {
  margin-top: 0;
}

.form-section-light {
  margin: 0;
  padding: 0;
  background-color: transparent;
  border: none;
}

.form-section-light label {
  display: block;
  margin: 0;
}

.form-section-light span {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.form-section-light input {
  width: 100%;
  padding: 0.5rem;
  box-sizing: border-box;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.form-section-light small {
  display: block;
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 400;
}

#image-preview-section {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1.5rem;
  align-items: start;
  margin-bottom: 1.5rem;
  padding: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background-color: var(--bg-secondary);
}

@media (max-width: 768px) {
  #image-preview-section {
    grid-template-columns: 1fr;
  }
}

.form-container {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background-color: var(--bg-secondary);
}

fieldset {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  margin: 1rem 0;
  padding: 1rem;
  background-color: var(--bg-secondary);
}

fieldset legend {
  padding: 0 0.5rem;
  font-weight: 600;
  color: var(--text-primary);
}

fieldset label {
  display: inline-block;
  margin-right: 1.5rem;
  margin-top: 0.5rem;
  width: auto;
}

fieldset input {
  width: auto;
  margin-right: 0.5rem;
}

button {
  margin-top: 1.5rem;
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  background-color: var(--button-bg);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

button:hover {
  background-color: var(--button-hover);
}

button:active {
  opacity: 0.9;
}

code {
  word-break: break-all;
  background-color: var(--bg-secondary);
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-size: 0.9em;
}

.metadata {
  background-color: var(--bg-secondary);
  padding: 0.75rem;
  margin-top: 0.5rem;
  border-radius: 4px;
  border-left: 3px solid var(--button-bg);
}

.suggestions {
  margin-top: 1rem;
}

.suggestion-button {
  display: inline-block;
  margin-right: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.4rem 0.8rem;
  background-color: var(--button-alt-bg);
  border: 1px solid var(--border-color);
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
  color: var(--text-primary);
}

.suggestion-button:hover {
  background-color: var(--button-alt-hover);
}

details {
  margin-bottom: 1.5rem;
  padding: 1rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--bg-secondary);
}

details summary {
  cursor: pointer;
  font-weight: 600;
  user-select: none;
}

details > div {
  margin-top: 1rem;
}

#image-preview-container {
  padding: 0.75rem;
  border-radius: 4px;
  background-color: var(--bg-secondary);
  display: none;
}

#image-preview-container.visible {
  display: block;
}

#image-preview {
  max-width: 200px;
  max-height: 200px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  display: block;
}

#image-dimensions {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.outcome-success {
  background-color: #d4edda;
  padding: 0.75rem;
  border-radius: 4px;
  border-left: 3px solid #28a745;
  color: #155724;
}

.outcome-failure {
  background-color: #f8d7da;
  padding: 0.75rem;
  border-radius: 4px;
  border-left: 3px solid #dc3545;
  color: #721c24;
}

@media (prefers-color-scheme: dark) {
  .outcome-success {
    background-color: #1e4620;
    border-left-color: #51cf66;
    color: #a6e22e;
  }

  .outcome-failure {
    background-color: #4a1c1c;
    border-left-color: #ff6b6b;
    color: #ff8a8a;
  }
}
"""

#: The form page. Every field is named for the ``GenerationRequest`` field it
#: fills, so :func:`nonogram.web.submission.read` is a lookup rather than a
#: translation table — with one exception the field's own label states: ``size``
#: is one box and ``GenerationRequest`` carries two sides, so a bare N fills
#: ``width`` and leaves ``height`` for the domain to derive from the source's
#: shape, exactly as a bare ``--size N`` does (FR-023, ADR-0022/R4), and an
#: explicit ``NxM`` fills both, exactly as an explicit ``--size NxM`` does
#: (CARD-028, ``submission._extent_token``).
#:
#: Nothing here constrains a value: no ``min``/``max`` on ``size``, no
#: ``pattern``, no numeric ``type``, no ``required``. An out-of-range ``size``
#: (``60``, ``60x60``) must reach the domain and be rejected there (AC-050,
#: ADR-0019/R1, guardrail G-2) — an HTML validation attribute would stop it in
#: the browser instead, which is the same mistake as putting ``choices=`` on
#: ``--difficulty`` (ADR-0010). A malformed ``size`` (``30x``, ``30X20``) is
#: refused by ``submission._extent_token`` before a request is built, exactly as
#: ``cli._extent_token`` refuses it for the CLI — a shape rule about the token's
#: *syntax*, not a value judgement about a puzzle, so it stays out of this
#: markup either way.
#:
#: CARD-032 restricted the form to image mode only: no source dropdown, no
#: library-key or density fields. The ``mode`` field is implicit (always
#: "image"), which :func:`nonogram.web.submission.from_fields` applies when
#: building the request. The urlencoded path still accepts all three modes
#: (guardrail G-2), handled by :data:`pages.MODES`'s unchanged validation.
FORM_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>nonogram</title>
<style>{_STYLE}</style>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  const form = document.querySelector('form');
  if (form) {{
    form.addEventListener('submit', function() {{
      const resultContainer = document.querySelector('[data-result-container]');
      if (resultContainer) {{
        resultContainer.innerHTML = '';
      }}
    }});
  }}
}});
</script>
</head>
<body>
<h1>nonogram</h1>
<p>Generate a uniquely-solvable black-and-white nonogram from an image you upload.
The same options the <code>nonogram generate --mode image</code> command takes;
the same pipeline behind them.</p>
<div data-result-container="true"></div>
<form method="post" action="{html.escape(FORM_ACTION)}" enctype="multipart/form-data">
  <input type="hidden" name="persisted_image_path" value="">
  <input type="hidden" name="persisted_image_filename" value="">

  <div id="image-preview-section">
    <div>
      <div id="image-preview-container">
        <img id="image-preview" alt="Preview of uploaded image">
        <div id="image-dimensions"></div>
      </div>
    </div>
    <div id="metadata-suggestions-area"></div>
  </div>

  <div class="form-container">
    <div class="form-grid">
      <div class="form-section-light">
        <label><span>Image</span>
          <input type="file" name="image">
          <small>select the picture to convert</small>
        </label>
      </div>

      <div class="form-section-light">
        <label><span>Size</span>
          <input type="text" name="size" placeholder="e.g., 20 or 20x30">
          <small>optional. One number for the grid's longer side (the other side follows the image's own shape), or WxH for exact width and height, e.g. 20x30</small>
        </label>
      </div>

      <div class="form-section">
        <h3>Export</h3>
        <fieldset>
          <legend>Formats</legend>
          {_checkboxes("export_formats", export.FORMATS, checked={"pdf"})}
        </fieldset>
        <label><span>Output directory <small>&mdash; defaults to the working directory</small></span>
          <input type="text" name="out" placeholder=".">
        </label>
      </div>

      <div class="form-section">
        <h3>Puzzle Settings</h3>
        <label><span>Difficulty</span>
          <select name="difficulty">
              {_options(list(difficulty.Tier), blank="(any)")}
          </select>
        </label>
        <label><span>Name <small>&mdash; shown on the printed page</small></span>
          <input type="text" name="name" placeholder="(auto-generated if empty)">
        </label>
        <label><span>Seed <small>&mdash; for a reproducible puzzle</small></span>
          <input type="text" name="seed" inputmode="numeric" placeholder="(random if empty)">
        </label>
      </div>
    </div>
  </div>

  <button type="submit">Generate</button>
</form>
<script src="/static/metadata.js"></script>
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
    * FR-014's **nudge count** is not reproduced. It can be non-zero now that
      an image-mode submission from this form carries a real picture
      (CARD-021's upload control), but reporting it is not this function's
      change to make — it stays owed to whichever later card first has a
      reason to show it, exactly as ``cli._run_generate``'s own nudge-count
      line was a separate addition to a result that already existed.

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
<p data-outcome="{SUCCESS}" class="outcome-success">Generated <strong>{html.escape(name or "")}</strong>.</p>
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
<p data-outcome="{FAILURE}" class="outcome-failure">{html.escape(summary)}</p>
<ul>
{listed}
</ul>""",
    )


def _form_field_value(fields: dict[str, list[str]], name: str) -> str:
    """Extract a single form field value for re-population.

    Returns the last value if multiple were sent, or empty string if absent.
    Escapes the value for safe interpolation into HTML attributes.
    """
    values = fields.get(name, [])
    value = values[-1] if values else ""
    return html.escape(value)


def _success_section(puzzle_name: str | None, seed: int, paths: Sequence[Path]) -> str:
    """Render an inline success result section (AC-122).

    Args:
        puzzle_name: The puzzle's name, or empty string if None.
        seed: The run's seed.
        paths: The files written.

    Returns:
        HTML markup for the success section, properly escaped.
    """
    if paths:
        written = "<ul>\n" + "\n".join(
            f"  <li><code>{html.escape(str(path))}</code></li>" for path in paths
        ) + "\n</ul>"
    else:
        written = "<p>No export format was requested, so no file was written.</p>"

    return f"""<details open>
  <summary aria-label="Puzzle generation success: name, seed, and written files"><strong data-outcome="{SUCCESS}" class="outcome-success">Generated</strong></summary>
  <div>
    <p>Name: <strong>{html.escape(puzzle_name or "")}</strong></p>
    <p>Seed: <code>{seed:d}</code></p>
    {written}
  </div>
</details>"""


def _error_section(summary: str, reasons: Sequence[str]) -> str:
    """Render an inline error result section (AC-123).

    Args:
        summary: One sentence describing the error.
        reasons: Detailed error messages.

    Returns:
        HTML markup for the error section, properly escaped.
    """
    listed = "\n".join(f"  <li>{html.escape(reason)}</li>" for reason in reasons)
    return f"""<details open>
  <summary aria-label="Generation failed with error details"><strong data-outcome="{FAILURE}" class="outcome-failure">Error</strong></summary>
  <div>
    <p>{html.escape(summary)}</p>
    <ul>
{listed}
    </ul>
  </div>
</details>"""



def _metadata_section(aspect_ratio_str: str) -> str:
    """Render the image metadata section (AC-125).

    Args:
        aspect_ratio_str: Formatted aspect ratio string (e.g., "4:3 (1.33)").

    Returns:
        HTML markup for the metadata section, properly escaped.
    """
    return f"""<div class="metadata">
  <p><strong>Image aspect ratio:</strong> {html.escape(aspect_ratio_str)}</p>
</div>"""


def _suggestions_section(suggestions: list[tuple[int, int]]) -> str:
    """Render suggested puzzle dimensions (AC-126).

    Args:
        suggestions: List of (width, height) tuples to suggest.

    Returns:
        HTML markup for the suggestions section, properly escaped.
    """
    if not suggestions:
        return ""
    
    buttons = []
    for width, height in suggestions:
        size_str = f"{width}x{height}"
        buttons.append(
            f'<button type="button" class="suggestion-button" '
            f'onclick="document.querySelector(\'input[name=\"size\"]\').value = {html.escape(size_str)!r};">'
            f'{html.escape(size_str)}</button>'
        )
    
    return f"""<div class="suggestions">
  <p><small><strong>Suggested dimensions (click to set):</strong></small></p>
  {" ".join(buttons)}
</div>"""


def form_with_result(
    fields: dict[str, list[str]],
    outcome: str,
    puzzle_name: str | None = None,
    seed: int = 0,
    paths: Sequence[Path] | None = None,
    error_summary: str = "",
    error_reasons: Sequence[str] | None = None,
    image_metadata_str: str = "",
    suggestions: list[tuple[int, int]] | None = None,
    persisted_image_path: str = "",
    persisted_image_metadata: dict | None = None,
    image_filename: str = "",
    persisted_image_filename: str = "",
) -> str:
    """Render the form page with an embedded result section (CARD-030).

    This renders the same form as FORM_PAGE but with values re-populated from
    the last submission, plus an inline collapsible result section showing either
    success or error outcome. Used instead of redirect pages after form submission.

    Mirrors FORM_PAGE's current form structure (CARD-032: image mode only).

    Args:
        fields: The parsed form fields from the submission (dict[name, [values]]).
        outcome: Either SUCCESS or FAILURE to indicate which result to show.
        puzzle_name: Name of the generated puzzle (success only).
        seed: The puzzle's seed (success only).
        paths: Files written (success only).
        error_summary: Error description (failure only).
        error_reasons: Detailed error messages (failure only).
        persisted_image_path: Path to uploaded image file for retry (CARD-037).
        persisted_image_metadata: Metadata dict with width, height, imageSrc (CARD-037).

    Returns:
        One complete HTML document with form and embedded result section.
    """
    result_html = ""
    if outcome == SUCCESS:
        result_html = _success_section(puzzle_name, seed, paths or [])
    elif outcome == FAILURE:
        result_html = _error_section(error_summary, error_reasons or [])

    # Re-populate form values from the submission (image mode only, CARD-032)
    size_val = _form_field_value(fields, "size")
    difficulty_val = _form_field_value(fields, "difficulty")
    name_val = _form_field_value(fields, "name")
    seed_val = _form_field_value(fields, "seed")
    out_val = _form_field_value(fields, "out")

    # Re-populate checkboxes for export_formats
    export_values = set(fields.get("export_formats", []))
    export_checkboxes = _checkboxes("export_formats", export.FORMATS, checked=export_values)

    # Show status message if image is persisted (CARD-037)
    persisted_status = (
        f'<div style="background-color: var(--bg-primary); color: var(--text-secondary); font-size: 0.875rem; margin-top: 0.5rem; padding: 0.5rem; border-radius: 3px; border-left: 3px solid var(--button-bg);">✓ Using: <strong>{html.escape(image_filename)}</strong> &mdash; modify size or settings and generate again without re-uploading. <small>(or upload a different image below)</small></div>'
        if persisted_image_path and image_filename else ""
    )

    form_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>nonogram</title>
<style>{_STYLE}</style>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  const form = document.querySelector('form');
  if (form) {{
    form.addEventListener('submit', function() {{
      const resultContainer = document.querySelector('[data-result-container]');
      if (resultContainer) {{
        resultContainer.innerHTML = '';
      }}
    }});
  }}
}});
</script>
</head>
<body>
<h1>nonogram</h1>
<p>Generate a uniquely-solvable black-and-white nonogram from an image you upload.
The same options the <code>nonogram generate --mode image</code> command takes;
the same pipeline behind them.</p>
<div data-result-container="true">
{result_html}
</div>
<form method="post" action="{html.escape(FORM_ACTION)}" enctype="multipart/form-data">
  <input type="hidden" name="persisted_image_path" value="{html.escape(persisted_image_path)}">
  <input type="hidden" name="persisted_image_filename" value="{html.escape(persisted_image_filename)}">

  <div id="image-preview-section">
    <div>
      <div id="image-preview-container">
        <img id="image-preview" alt="Preview of uploaded image">
        <div id="image-dimensions"></div>
      </div>
    </div>
    <div id="metadata-suggestions-area"></div>
  </div>

  <div class="form-container">
    <div class="form-grid">
      <div class="form-section-light">
        <label><span>Image</span>
          <input type="file" name="image">
          <small>select the picture to convert</small>
        </label>
        {persisted_status}
      </div>

      <div class="form-section-light">
        <label><span>Size</span>
          <input type="text" name="size" value="{size_val}" placeholder="e.g., 20 or 20x30">
          <small>optional. One number for the grid's longer side (the other side follows the image's own shape), or WxH for exact width and height, e.g. 20x30</small>
        </label>
      </div>

      <div class="form-section">
        <h3>Export</h3>
        <fieldset>
          <legend>Formats</legend>
          {export_checkboxes}
        </fieldset>
        <label><span>Output directory <small>&mdash; defaults to the working directory</small></span>
          <input type="text" name="out" value="{out_val}" placeholder=".">
        </label>
      </div>

      <div class="form-section">
        <h3>Puzzle Settings</h3>
        <label><span>Difficulty</span>
          <select name="difficulty">
              {_options(list(difficulty.Tier), blank="(any)", selected=difficulty_val)}
          </select>
        </label>
        <label><span>Name <small>&mdash; shown on the printed page</small></span>
          <input type="text" name="name" value="{name_val}" placeholder="(auto-generated if empty)">
        </label>
        <label><span>Seed <small>&mdash; for a reproducible puzzle</small></span>
          <input type="text" name="seed" inputmode="numeric" value="{seed_val}" placeholder="(random if empty)">
        </label>
      </div>
    </div>
  </div>

  <button type="submit">Generate</button>
</form>
<script>
// AC-124: Collapse result section and manage focus when user interacts with form
document.addEventListener('DOMContentLoaded', function() {{
  var resultDetails = document.querySelector('details');
  var formInputs = document.querySelectorAll('input, select, textarea');
  if (resultDetails && formInputs.length > 0) {{
    formInputs.forEach(function(input) {{
      input.addEventListener('input', function() {{
        resultDetails.open = false;
      }});
    }});
  }}
}});
</script>"""

    # Add persisted image metadata script tag if metadata is provided (CARD-037)
    if persisted_image_metadata:
        metadata_json = json.dumps(persisted_image_metadata)
        form_html += f"""
<script type="application/json" data-image-metadata>
{metadata_json}
</script>"""

    form_html += """
<script src="/static/metadata.js"></script>
</body>
</html>
"""
    return form_html
