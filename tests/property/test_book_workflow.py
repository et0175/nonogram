"""CARD-131 — the two standing properties of the book workflow.

    EC-026  PropertyTest_BookWorkflow_BackNavigationNeverDiscardsLaterWork
            For any book and any sequence of step visits and plan edits, the
            selection set, the arrangement order and the custom titles change
            only through an explicit add, remove, reorder or retitle — never as
            a side effect of revisiting a step or editing the plan.

    EC-033  PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists
            For any book, any starting status and any sequence of adds and
            removes over every route, a book whose membership differs from the
            membership it last left draft with is in draft.

Both are stated over *sequences*, so both are driven as sequences: a seeded
corpus of operation orders, each replayed against a real panel through the
Flask test client, with the assertion made after **every** step rather than at
the end of the run. A property that only held at the end of a sequence would be
satisfied by a book that spent the middle of it wrong.

No ``hypothesis`` (it is not in the dependency baseline): the corpus is built by
hand with stdlib :class:`random.Random` on a fixed seed, and the case counts —
total, and per operation kind — are asserted *inside* each test, so the corpus
cannot silently shrink into a green that means nothing. A run in which no add
ever happened, or in which the book never left draft, would satisfy either
property vacuously, and each test refuses to pass on one.

EC-033's expectations are computed by this file, not by the code under test:
the plan a promotion needs is built from :func:`count_cells` here — a second,
independent implementation of the bucketing ``book_plan.selection_cells``
does — over the sizes and tiers this file gave the puzzles it created.
"""

from __future__ import annotations

import random
from collections import Counter

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager, BookStatus, DistributionPlan, Split
from nonogram.admin.book_plan import BUCKETS, TIERS
from tests.test_book_ready_gate import Shelf

DRAFT = BookStatus.DRAFT.value
OUT_OF_DRAFT = tuple(s.value for s in BookStatus if s is not BookStatus.DRAFT)

#: The seed. Fixed, so a failure is reproducible and a corpus is a corpus.
SEED = 20260924 + 131

#: EC-026's corpus: how many sequences, how long, and the smallest number of
#: decisions of each kind a run must hold.
EC026_SEQUENCES = 24
EC026_STEPS = 12
EC026_MIN_OPERATIONS = 250
EC026_MIN_OF_EACH_KIND = 12

#: EC-033's corpus.
EC033_SEQUENCES = 18
EC033_STEPS = 10
EC033_MIN_OPERATIONS = 150
#: A run that never promoted a book, or never changed a membership afterwards,
#: proves nothing about "outside draft". Both are asserted.
EC033_MIN_PROMOTIONS = 12
EC033_MIN_MEMBERSHIP_CHANGES = 40

#: The inclusive longest-side range of each bucket, in BUCKETS order, written
#: out here rather than read off ``LongestSideBucket.low/high``: this file's
#: counting must be able to disagree with the code under test (CLAUDE.md's
#: "prefer an independent second implementation").
BUCKET_RANGES = ((10, 15), (16, 20), (21, 25), (26, 30))

#: The tiers, likewise written out, in the order the matrix's columns run.
TIER_NAMES = ("easy", "medium", "hard")


def count_cells(records) -> dict:
    """``{(bucket index, tier index): count}`` for a selection of records.

    An independent second implementation of ``book_plan.selection_cells``: a
    linear scan of :data:`BUCKET_RANGES` rather than that module's bucketing,
    over the width, height and tier this file stored itself.
    """
    counts = {(b, t): 0 for b in range(len(BUCKET_RANGES)) for t in range(len(TIER_NAMES))}
    for record in records:
        longest = max(record["width"], record["height"])
        buckets = [i for i, (low, high) in enumerate(BUCKET_RANGES) if low <= longest <= high]
        if len(buckets) != 1 or record["difficulty_tier"] not in TIER_NAMES:
            continue
        counts[(buckets[0], TIER_NAMES.index(record["difficulty_tier"]))] += 1
    return counts


def plan_for(records) -> DistributionPlan:
    """The plan a selection of ``records`` passes ADR-0035's gate exactly on.

    Every cell on its own count, and the count the selection's own size, so no
    cell is any distance from its plan. The split is not what the gate measures
    (that is the matrix) and only has to be three whole percents summing to 100
    for INV-005, so it is written as one.
    """
    cells = count_cells(records)
    return DistributionPlan(
        count=max(1, len(records)),
        split=Split(100, 0, 0),
        cells=tuple(
            tuple(cells[(b, t)] for t in range(len(TIER_NAMES)))
            for b in range(len(BUCKET_RANGES))
        ),
    )


# --------------------------------------------------------------------------
# One panel, and the books these properties are replayed against
# --------------------------------------------------------------------------


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode, and a shelf over its own store and books."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))

    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    shelf = Shelf("memory", None, store=app.puzzle_review_service, books=app.book_manager)
    return app, shelf


def make_puzzles(shelf, rng, count):
    """``count`` stored puzzles spread over the buckets and tiers."""
    wanted = {}
    for _ in range(count):
        cell = (rng.choice(BUCKETS), rng.choice(TIERS))
        wanted[cell] = wanted.get(cell, 0) + 1
    ids = []
    for cell, many in wanted.items():
        ids.extend(shelf.puzzles({cell: many}))
    rng.shuffle(ids)
    return ids


def membership(shelf, book_id):
    return list(shelf.books.get_book(book_id).puzzle_ids)


def titles(shelf, book_id):
    return dict(shelf.books.get_book(book_id).puzzle_titles or {})


def status(shelf, book_id):
    return shelf.books.get_book(book_id).status


def records(shelf, puzzle_ids):
    return [shelf.store.get_puzzle(pid) for pid in puzzle_ids]


# --------------------------------------------------------------------------
# EC-026 — revisiting a step, or editing the plan, discards nothing
# --------------------------------------------------------------------------

#: The operations that must leave the selection, the order and the titles
#: exactly as they were. Each is a real request against a real route.
PASSIVE = (
    "visit_detail",
    "visit_print_setup",
    "visit_selection",
    "visit_arrangement",
    "visit_finalise",
    "visit_books",
    "edit_plan",
    "switch_tab",
    "page_of_tab",
    "clear_ticks",
)

#: The operations that are allowed to change it — the four EC-026 names.
EXPLICIT = ("add", "remove", "reorder", "retitle")


def _plan_form(count):
    """A complete Print setup submission carrying a plan of ``count``."""
    form = {"unit": "cm", "width": "21.59", "height": "27.94", "plan_count": str(count)}
    for tier, share in zip(TIER_NAMES, (40, 40, 20)):
        form[f"split_{tier}"] = str(share)
    for b in range(len(BUCKET_RANGES)):
        for tier in TIER_NAMES:
            form[f"cell_{b}_{tier}"] = "0"
    return form


def test_PropertyTest_BookWorkflow_BackNavigationNeverDiscardsLaterWork(panel) -> None:
    """EC-026 — only an explicit add, remove, reorder or retitle changes the work.

    The property is checked as an equality after **every** operation: a passive
    one must leave ``(order, titles)`` identical, and an explicit one re-bases
    the expectation on whatever it produced. Stated that way it needs no model
    of what an add does — it needs only that nothing else does anything.
    """
    app, shelf = panel
    rng = random.Random(SEED)
    performed: Counter = Counter()

    for sequence in range(EC026_SEQUENCES):
        client = app.test_client()
        spare = make_puzzles(shelf, rng, 6)
        seeded = make_puzzles(shelf, rng, 6)
        book_id = shelf.books.create_book(
            f"Winter {sequence}", "a book", "christmas", "adults"
        )
        shelf.books.add_puzzles_to_book(book_id, seeded)
        for puzzle_id in seeded[:3]:
            shelf.books.set_puzzle_title(book_id, puzzle_id, f"Title {puzzle_id[:4]}")
        expected = (membership(shelf, book_id), titles(shelf, book_id))

        for _ in range(EC026_STEPS):
            held = membership(shelf, book_id)
            operation = rng.choice(PASSIVE + EXPLICIT if (held and spare) else PASSIVE)
            performed[operation] += 1
            _perform(client, book_id, operation, held, spare, rng)
            now = (membership(shelf, book_id), titles(shelf, book_id))

            if operation in PASSIVE:
                assert now == expected, (
                    f"{operation!r} changed the book's work: {expected} became {now}"
                )
            else:
                expected = now

    assert sum(performed.values()) >= EC026_MIN_OPERATIONS, performed
    for operation in PASSIVE + EXPLICIT:
        assert performed[operation] >= EC026_MIN_OF_EACH_KIND, (
            f"the corpus barely exercised {operation!r}: {performed}"
        )


def _perform(client, book_id, operation, held, spare, rng) -> None:
    """One operation, as the product performs it — through its own route."""
    if operation == "visit_detail":
        assert client.get(f"/book/{book_id}").status_code == 200
    elif operation == "visit_print_setup":
        assert client.get(f"/book/{book_id}/setup-print").status_code == 200
    elif operation == "visit_selection":
        assert client.get(f"/book/{book_id}/select-puzzles").status_code == 200
    elif operation == "visit_arrangement":
        assert client.get(f"/book/{book_id}/arrange-puzzles").status_code == 200
    elif operation == "visit_finalise":
        assert client.get(f"/book/{book_id}/finalize").status_code == 200
    elif operation == "visit_books":
        assert client.get("/books").status_code == 200
    elif operation == "edit_plan":
        client.post(
            f"/book/{book_id}/setup-print", data=_plan_form(rng.choice((60, 90, 120, 150)))
        )
    elif operation == "switch_tab":
        client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "<=15", "go_bucket": rng.choice([b.label for b in BUCKETS])},
        )
    elif operation == "page_of_tab":
        client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "16-20", "go_offset": "0"},
        )
    elif operation == "clear_ticks":
        client.post(
            f"/book/{book_id}/select-puzzles", data={"bucket": "<=15", "go_clear": "1"}
        )
    elif operation == "add":
        joining = spare.pop()
        client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "<=15", "shown_ids": [joining], "puzzle_ids": [joining]},
        )
    elif operation == "remove":
        client.post(
            f"/book/{book_id}/remove-puzzle", data={"puzzle_id": rng.choice(held)}
        )
    elif operation == "reorder":
        client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={
                "action": rng.choice(("move_up", "move_down")),
                "puzzle_id": rng.choice(held),
            },
        )
    elif operation == "retitle":
        client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={
                "action": "set_title",
                "puzzle_id": rng.choice(held),
                "title": f"Picture {rng.randrange(1000)}",
            },
        )
    else:  # pragma: no cover - the corpus draws from the two tuples only
        raise AssertionError(f"unknown operation {operation!r}")


# --------------------------------------------------------------------------
# EC-033 — a changed membership never persists outside draft
# --------------------------------------------------------------------------

#: Every route that ends in the book store, which is what EC-033 quantifies
#: over. The arrange step's Delete is here too: it is a membership route, and
#: the rule is the store's rather than any one route's.
MEMBERSHIP_ROUTES = ("selection_step", "paste_ids", "remove_route", "arrange_delete")


def test_PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists(
    panel,
) -> None:
    """EC-033 (INV-012) — no route leaves a non-draft book holding a change.

    The book is promoted out of draft through the real status route, so every
    promotion in the corpus is one ADR-0035's plan gate actually let through,
    and the membership it left draft with is recorded at that moment. After
    **every** subsequent operation the property is checked directly: if the
    book is not in draft, its membership is that recorded one, id for id.
    """
    app, shelf = panel
    rng = random.Random(SEED + 1)
    performed: Counter = Counter()
    promotions = 0
    membership_changes = 0

    for sequence in range(EC033_SEQUENCES):
        client = app.test_client()
        spare = make_puzzles(shelf, rng, 8)
        seeded = make_puzzles(shelf, rng, 6)
        book_id = shelf.books.create_book(
            f"Autumn {sequence}", "a book", "generic", "adults"
        )
        shelf.books.add_puzzles_to_book(book_id, seeded)
        left_draft_with = None

        for _ in range(EC033_STEPS):
            held = membership(shelf, book_id)
            before = list(held)
            if status(shelf, book_id) == DRAFT and held and rng.random() < 0.45:
                # Promote: store the plan this selection is exactly on, then
                # ask the route to leave draft. Both are things the owner does.
                shelf.books.save_plan(book_id, plan_for(records(shelf, held)))
                target = rng.choice(OUT_OF_DRAFT)
                client.post(f"/book/{book_id}/status", data={"status": target})
                performed["promote"] += 1
                if status(shelf, book_id) != DRAFT:
                    promotions += 1
                    left_draft_with = list(membership(shelf, book_id))
            else:
                route = rng.choice(MEMBERSHIP_ROUTES)
                performed[route] += 1
                _change(client, book_id, route, held, spare, rng)
                if membership(shelf, book_id) != before:
                    membership_changes += 1

            if status(shelf, book_id) != DRAFT:
                assert left_draft_with is not None, (
                    "the book is outside draft without ever having left it"
                )
                assert membership(shelf, book_id) == left_draft_with, (
                    "a non-draft book holds a membership it never passed the "
                    f"plan check with: {membership(shelf, book_id)} against "
                    f"{left_draft_with}"
                )

    assert sum(performed.values()) >= EC033_MIN_OPERATIONS, performed
    for route in MEMBERSHIP_ROUTES:
        assert performed[route] >= 10, f"route {route!r} barely ran: {performed}"
    assert promotions >= EC033_MIN_PROMOTIONS, (
        f"the corpus never really left draft, so it proves nothing: {promotions}"
    )
    assert membership_changes >= EC033_MIN_MEMBERSHIP_CHANGES, (
        f"the corpus barely changed a membership: {membership_changes}"
    )

def _change(client, book_id, route, held, spare, rng) -> None:
    """One membership change over one route, confirming when asked to."""
    if route in ("remove_route", "arrange_delete") and not held:
        route = "paste_ids"
    if route in ("selection_step", "paste_ids") and not spare:
        route = "remove_route" if held else "selection_step"

    if route == "selection_step" and spare:
        joining = spare.pop()
        response = client.post(
            f"/book/{book_id}/select-puzzles",
            data={"bucket": "<=15", "shown_ids": [joining], "puzzle_ids": [joining]},
        )
    elif route == "paste_ids" and spare:
        response = client.post(
            f"/book/{book_id}/add-puzzles", data={"puzzle_ids": spare.pop()}
        )
    elif route == "remove_route" and held:
        response = client.post(
            f"/book/{book_id}/remove-puzzle", data={"puzzle_id": rng.choice(held)}
        )
    elif route == "arrange_delete" and held:
        response = client.post(
            f"/book/{book_id}/arrange-puzzles",
            data={"action": "delete", "puzzle_id": rng.choice(held)},
        )
    else:
        return

    # A published book asks first (INV-008). The owner confirms, which is
    # the branch EC-033 has to hold over: the change lands *and* the book
    # comes back to draft in the same write.
    if b"Confirm change" in response.data:
        _confirm(client, response)


def _confirm(client, response) -> None:
    """Press the rendered "Confirm change" button, posting its own fields back."""
    import html as html_module
    import re

    body = response.get_data(as_text=True)
    forms = re.findall(r"(?s)<form\b[^>]*\baction=\"([^\"]*)\"[^>]*>(.*?)</form>", body)
    assert len(forms) == 1, "the confirmation page must carry exactly one form"
    action, inner = forms[0]
    form: dict = {}
    for name, value in re.findall(
        r"<input\b[^>]*\btype=\"hidden\"[^>]*\bname=\"([^\"]*)\"[^>]*\bvalue=\"([^\"]*)\"[^>]*>",
        inner,
    ):
        form.setdefault(html_module.unescape(name), []).append(html_module.unescape(value))
    client.post(html_module.unescape(action), data=form, follow_redirects=True)
