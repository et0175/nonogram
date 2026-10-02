"""CARD-159 AC-3 — a refused ``/book/create`` keeps what the owner typed.

    AC-3    TestBookCreate_RefusalKeepsTypedInput

The create route used to flash its error and re-render an empty New book
form, so a title of spaces — which the browser's ``required`` lets through
and the domain refuses — threw the description, theme and audience away.
It now carries the submission back and marks the refused field, the way the
edit route has since CARD-130.

Driven through the Flask test client against the real route (no browser
harness exists). The rendered form is read back with an independent HTML
parser rather than substring searches, so a value is checked as the browser
would see it — which is also what makes the escaping check meaningful: a
value that broke out of its attribute would parse as a different value.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager

#: A complete, valid New book submission. Each refusal case below breaks
#: exactly one field of it.
VALID = {
    "title": "Winter Birds",
    "description": "Forty festive puzzles for long evenings",
    "theme": "halloween",
    "target_audience": "seniors",
}

#: One refusal per rule the domain applies, written out: the field the
#: submission breaks and the value it breaks it with.
REFUSALS = (
    ("title", "   "),
    ("description", "  "),
    ("theme", "not-a-theme"),
    ("target_audience", ""),
)


class _Form(HTMLParser):
    """The New book form's four controls, as the browser would read them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attrs: dict = {}
        self.values: dict = {}
        self.ids: set = set()
        self._textarea = None
        self._select = None

    def handle_starttag(self, tag, attrs) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        name = attributes.get("name")
        if tag == "input" and name in ("title", "target_audience"):
            self.attrs[name] = attributes
            self.values[name] = attributes.get("value", "")
        elif tag == "textarea" and name == "description":
            self.attrs[name] = attributes
            self.values[name] = ""
            self._textarea = name
        elif tag == "select" and name == "theme":
            self.attrs[name] = attributes
            self.values.setdefault(name, None)
            self._select = name
        elif tag == "option" and self._select and "selected" in attributes:
            self.values[self._select] = attributes.get("value")

    def handle_endtag(self, tag) -> None:
        if tag == "textarea":
            self._textarea = None
        elif tag == "select":
            self._select = None

    def handle_data(self, data) -> None:
        if self._textarea:
            self.values[self._textarea] += data

    def marked(self) -> set:
        """Controls marked invalid — class, ARIA and a reachable description together."""
        invalid = set()
        for name, attributes in self.attrs.items():
            classes = (attributes.get("class") or "").split()
            if "is-invalid" not in classes and attributes.get("aria-invalid") != "true":
                continue
            assert "is-invalid" in classes, name
            assert attributes.get("aria-invalid") == "true", name
            assert attributes.get("aria-describedby") in self.ids, name
            invalid.add(name)
        return invalid


def form_of(body: str) -> _Form:
    read = _Form()
    read.feed(body)
    assert set(read.attrs) == {"title", "description", "theme", "target_audience"}
    return read


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode (never a real database)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))

    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def _book_count(app) -> int:
    return len(app.book_manager.get_all_books())


class TestBookCreate_RefusalKeepsTypedInput:
    """AC-3 — the refused form comes back with the submitted values filled in."""

    @pytest.mark.parametrize("field,bad", REFUSALS)
    def test_every_refusal_carries_the_submission_back(self, panel, field, bad) -> None:
        submission = {**VALID, field: bad}
        before = _book_count(panel)

        with panel.test_client() as client:
            response = client.post("/book/create", data=submission)
            body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert _book_count(panel) == before, "a refused create stored a book"
        read = form_of(body)
        for name, value in submission.items():
            if name == "theme" and field == "theme":
                # An unknown theme has no <option> to select; the select
                # simply shows no stored choice. The other three still come back.
                assert read.values["theme"] is None
                continue
            assert read.values[name] == value, f"{name} came back as {read.values[name]!r}"

    @pytest.mark.parametrize("field,bad", REFUSALS)
    def test_the_refused_field_alone_is_marked(self, panel, field, bad) -> None:
        with panel.test_client() as client:
            body = client.post("/book/create", data={**VALID, field: bad}).get_data(as_text=True)

        assert form_of(body).marked() == {field}
        assert 'id="general-info-error"' in body

    def test_a_value_with_html_specials_is_escaped_not_injected(self, panel) -> None:
        """Autoescaping holds on the carried-back values.

        A title that closed its own attribute, and a description that closed
        the textarea, would each parse back as something else — and the
        injected ``<script>`` would be a real element.
        """
        title = '"><script>alert(1)</script> & <b>bold</b>'
        description = "</textarea><script>alert(2)</script>"
        audience = "kids & 'grown-ups'"

        with panel.test_client() as client:
            body = client.post(
                "/book/create",
                data={
                    "title": title,
                    "description": description,
                    # A refusal, so the values are carried back: an unknown
                    # theme is the one rule these three values do not trip.
                    "theme": "nope",
                    "target_audience": audience,
                },
            ).get_data(as_text=True)

        read = form_of(body)
        assert read.values["title"] == title
        assert read.values["description"] == description
        assert read.values["target_audience"] == audience
        assert "<script>alert(1)</script>" not in body
        assert "<script>alert(2)</script>" not in body
        assert "&lt;script&gt;" in body

    def test_a_refusal_naming_no_field_still_carries_the_input_back(
        self, panel, monkeypatch
    ) -> None:
        """A plain ``ValueError`` (no ``fields``) keeps the input and marks nothing."""

        def refuse(**_kwargs):
            raise ValueError("storage said no")

        monkeypatch.setattr(panel.book_manager, "create_book", refuse)

        with panel.test_client() as client:
            response = client.post("/book/create", data=VALID)
            body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "storage said no" in body
        read = form_of(body)
        assert read.values == VALID
        assert read.marked() == set()

    def test_a_fresh_form_is_empty_and_unmarked(self, panel) -> None:
        with panel.test_client() as client:
            body = client.get("/book/create").get_data(as_text=True)

        read = form_of(body)
        assert read.values["title"] == ""
        assert read.values["description"] == ""
        assert read.values["target_audience"] == ""
        assert read.marked() == set()

    def test_a_valid_submission_still_creates_and_moves_on(self, panel) -> None:
        before = _book_count(panel)

        with panel.test_client() as client:
            response = client.post("/book/create", data=VALID)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/setup-print")
        assert _book_count(panel) == before + 1
