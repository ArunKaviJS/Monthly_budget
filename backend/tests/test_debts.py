"""
test_debts.py — Money given to / got from other people, kept inside a book.

lent = I gave (they owe me), borrowed = I got (I owe them). A debt stays
pending until returned; the pending count drives the app's notification badge.
"""


import pytest

from app import database
from app.intent_engine import _get_today


@pytest.fixture
def me(alice):
    """Alice with an active book, ready to note debts."""
    alice.post("/api/books", json={"name": "Home"})
    return alice


def _add(c, person="Ravi", amount=500, direction="lent", **extra):
    r = c.post("/api/debts", json={"person": person, "amount": amount, "direction": direction, **extra})
    assert r.status_code == 201, r.text
    return r.json()


# ═══════════════════════════════════════════════
# Adding
# ═══════════════════════════════════════════════
def test_add_a_debt_i_gave_with_person_reason_and_date(me):
    d = _add(me, "Ravi", 500, "lent", reason="Phone recharge", date="2026-09-10")
    assert d["person"] == "Ravi"
    assert d["reason"] == "Phone recharge"
    assert d["date"] == "2026-09-10"
    assert d["amount"] == "500.00"
    assert d["direction"] == "lent"
    assert d["status"] == "pending"
    assert d["settled_on"] is None


def test_add_a_debt_i_got_from_someone(me):
    d = _add(me, "Meena", 1200, "borrowed", reason="Rent shortfall")
    assert d["direction"] == "borrowed"
    assert d["status"] == "pending"


def test_date_defaults_to_today_and_reason_is_optional(me):
    d = _add(me, "Ravi", 100)
    assert d["reason"] is None
    assert d["date"] == _get_today().isoformat()  # "today" as the app defines it (IST)


def test_debt_is_filed_in_the_active_book(me):
    book = me.get("/api/books/active").json()
    assert _add(me)["book_id"] == book["id"]


def test_cannot_add_a_debt_without_a_book(alice):
    r = alice.post("/api/debts", json={"person": "Ravi", "amount": 10, "direction": "lent"})
    assert r.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"person": "", "amount": 10, "direction": "lent"},
        {"person": "   ", "amount": 10, "direction": "lent"},
        {"person": "Ravi", "amount": 0, "direction": "lent"},
        {"person": "Ravi", "amount": -5, "direction": "lent"},
        {"person": "Ravi", "amount": 10, "direction": "gift"},
        {"person": "Ravi", "amount": 10},  # missing direction
        {"person": "x" * 61, "amount": 10, "direction": "lent"},
        {"person": "Ravi", "amount": 10, "direction": "lent", "reason": "r" * 201},
    ],
)
def test_invalid_debt_is_rejected(me, payload):
    assert me.post("/api/debts", json=payload).status_code == 422


def test_bad_date_is_rejected_with_a_clear_message(me):
    r = me.post("/api/debts", json={"person": "Ravi", "amount": 10, "direction": "lent", "date": "not a date"})
    assert r.status_code == 422
    assert "YYYY-MM-DD" in r.json()["detail"]


# ═══════════════════════════════════════════════
# Pending -> returned (the badge)
# ═══════════════════════════════════════════════
def test_pending_debts_show_on_the_book_and_hide_when_returned(me):
    assert me.get("/api/books/active").json()["pending_debts"] == 0

    a = _add(me, "Ravi", 500, "lent")
    b = _add(me, "Meena", 200, "borrowed")
    assert me.get("/api/books/active").json()["pending_debts"] == 2

    me.patch(f"/api/debts/{a['id']}", json={"status": "settled"})
    assert me.get("/api/books/active").json()["pending_debts"] == 1

    me.patch(f"/api/debts/{b['id']}", json={"status": "settled"})
    assert me.get("/api/books/active").json()["pending_debts"] == 0  # badge hides


def test_marking_returned_records_when(me):
    d = _add(me)
    r = me.patch(f"/api/debts/{d['id']}", json={"status": "settled", "settled_on": "2026-09-15"})
    assert r.status_code == 200
    assert r.json()["status"] == "settled"
    assert r.json()["settled_on"] == "2026-09-15"


def test_returned_defaults_to_today(me):
    d = _add(me)
    r = me.patch(f"/api/debts/{d['id']}", json={"status": "settled"})
    assert r.json()["settled_on"] is not None


def test_undo_returns_a_debt_to_pending(me):
    d = _add(me)
    me.patch(f"/api/debts/{d['id']}", json={"status": "settled"})
    r = me.patch(f"/api/debts/{d['id']}", json={"status": "pending"})
    assert r.json()["status"] == "pending"
    assert r.json()["settled_on"] is None
    assert me.get("/api/books/active").json()["pending_debts"] == 1


def test_summary_shows_what_i_will_get_and_what_i_owe(me):
    _add(me, "Ravi", 500, "lent")
    _add(me, "Kumar", 250, "lent")
    b = _add(me, "Meena", 200, "borrowed")
    s = me.get("/api/debts/summary").json()
    assert s["pending_count"] == 3
    assert float(s["lent_pending"]) == 750.0
    assert float(s["borrowed_pending"]) == 200.0

    me.patch(f"/api/debts/{b['id']}", json={"status": "settled"})
    s = me.get("/api/debts/summary").json()
    assert s["pending_count"] == 2 and float(s["borrowed_pending"]) == 0.0


# ═══════════════════════════════════════════════
# Listing, editing, deleting
# ═══════════════════════════════════════════════
def test_list_filters_by_status(me):
    a = _add(me, "Ravi")
    _add(me, "Meena")
    me.patch(f"/api/debts/{a['id']}", json={"status": "settled"})
    assert [d["person"] for d in me.get("/api/debts", params={"status": "pending"}).json()] == ["Meena"]
    assert [d["person"] for d in me.get("/api/debts", params={"status": "settled"}).json()] == ["Ravi"]
    assert len(me.get("/api/debts").json()) == 2


def test_edit_a_debt(me):
    d = _add(me, "Ravi", 500, "lent", reason="Old")
    r = me.patch(f"/api/debts/{d['id']}", json={"person": "Ravi K", "amount": 650, "reason": "New", "date": "2026-08-01"})
    assert r.status_code == 200
    body = r.json()
    assert (body["person"], body["amount"], body["reason"], body["date"]) == ("Ravi K", "650.00", "New", "2026-08-01")


def test_delete_a_debt(me):
    d = _add(me)
    assert me.delete(f"/api/debts/{d['id']}").status_code == 204
    assert me.get("/api/debts").json() == []
    assert me.delete(f"/api/debts/{d['id']}").status_code == 404
    assert me.get("/api/books/active").json()["pending_debts"] == 0


def test_missing_debt_is_404(me):
    assert me.patch("/api/debts/9999", json={"status": "settled"}).status_code == 404


# ═══════════════════════════════════════════════
# Kept inside the book
# ═══════════════════════════════════════════════
def test_each_book_has_its_own_debts(me):
    home = me.get("/api/books/active").json()
    _add(me, "Ravi", 500)
    trip = me.post("/api/books", json={"name": "Trip"}).json()
    _add(me, "Meena", 300, "borrowed")

    assert [d["person"] for d in me.get("/api/debts", params={"book_id": home["id"]}).json()] == ["Ravi"]
    assert [d["person"] for d in me.get("/api/debts", params={"book_id": trip["id"]}).json()] == ["Meena"]

    books = {b["name"]: b for b in me.get("/api/books").json()}
    assert books["Home"]["pending_debts"] == 1 and books["Trip"]["pending_debts"] == 1
    assert me.get("/api/debts/summary", params={"book_id": home["id"]}).json()["pending_count"] == 1


def test_deleting_a_book_deletes_its_debts_from_the_database(me):
    book = me.get("/api/books/active").json()
    d = _add(me)
    me.post("/api/books", json={"name": "Other"})
    _add(me, "Kept", 10)

    me.delete(f"/api/books/{book['id']}")
    db = database.get_db()
    assert db.debts.count_documents({"_id": d["id"]}) == 0
    assert db.debts.count_documents({}) == 1  # the other book's debt survives


# ═══════════════════════════════════════════════
# Nothing else changes
# ═══════════════════════════════════════════════
def test_debts_are_never_counted_as_expenses(me):
    me.post("/api/expenses", json={"raw_text": "tea 20"})
    before_book = me.get("/api/books/active").json()
    before_summary = me.get("/api/summary").json()

    _add(me, "Ravi", 5000, "lent")
    _add(me, "Meena", 3000, "borrowed")

    after_book = me.get("/api/books/active").json()
    assert after_book["total"] == before_book["total"] and after_book["count"] == before_book["count"]
    assert me.get("/api/summary").json()["total"] == before_summary["total"]
    assert len(me.get("/api/expenses").json()) == 1
    assert "Ravi" not in me.get("/api/export/csv").text


def test_delete_all_expenses_leaves_debts_alone(me):
    me.post("/api/expenses", json={"raw_text": "tea 20"})
    _add(me)
    me.delete("/api/expenses")
    assert len(me.get("/api/debts").json()) == 1


# ═══════════════════════════════════════════════
# Privacy between users
# ═══════════════════════════════════════════════
def test_debts_are_private_to_each_user(me, bob):
    bob.post("/api/books", json={"name": "Bob Book"})
    d = _add(me, "Ravi", 500)
    _add(bob, "Sita", 100)

    assert [x["person"] for x in me.get("/api/debts").json()] == ["Ravi"]
    assert [x["person"] for x in bob.get("/api/debts").json()] == ["Sita"]

    assert bob.patch(f"/api/debts/{d['id']}", json={"status": "settled"}).status_code == 404
    assert bob.delete(f"/api/debts/{d['id']}").status_code == 404
    assert me.get("/api/debts").json()[0]["status"] == "pending"  # untouched

    assert me.get("/api/books/active").json()["pending_debts"] == 1
    assert float(bob.get("/api/debts/summary").json()["lent_pending"]) == 100.0


@pytest.mark.parametrize(
    "method,path",
    [("get", "/api/debts"), ("post", "/api/debts"), ("get", "/api/debts/summary"),
     ("patch", "/api/debts/1"), ("delete", "/api/debts/1")],
)
def test_debt_endpoints_need_sign_in(anon, method, path):
    assert getattr(anon, method)(path).status_code == 401
