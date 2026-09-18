"""
test_api.py — End-to-end API tests, run as a signed-in user ("alice").

Covers the full flow the mobile app depends on: books, adding expenses (text +
manual + user-picked category), list/filter, preview, edit (with learning),
delete one / all, budgets, keywords, summary, export and validation errors.
Accounts, tokens and per-user isolation are in test_auth.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import signup

client = TestClient(app)


@pytest.fixture(autouse=True)
def signed_in_as_alice(fresh_database):
    """Sign up a fresh user for every test and give them a book
    (expense creation requires an active book)."""
    data = signup(TestClient(app), "alice")
    client.headers.update({"Authorization": f"Bearer {data['token']}"})
    client.post("/api/books", json={"name": "Test Book"})
    yield


# ═══════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════
def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ═══════════════════════════════════════════════
# Books
# ═══════════════════════════════════════════════
def test_create_book_becomes_active():
    r = client.post("/api/books", json={"name": "September"})
    assert r.status_code == 201
    assert r.json()["is_active"] is True

    active = client.get("/api/books/active")
    assert active.status_code == 200
    assert active.json()["name"] == "September"


def test_creating_a_book_deactivates_the_previous_one():
    b1 = client.post("/api/books", json={"name": "Book 1"}).json()
    client.post("/api/books", json={"name": "Book 2"})

    books = client.get("/api/books").json()
    b1_after = next(b for b in books if b["id"] == b1["id"])
    assert b1_after["is_active"] is False


def test_create_book_rejects_empty_name():
    r = client.post("/api/books", json={"name": "   "})
    assert r.status_code == 422


def test_rename_and_reactivate_book():
    b1 = client.post("/api/books", json={"name": "Old Name"}).json()
    client.post("/api/books", json={"name": "Other"})  # deactivates b1

    r = client.patch(f"/api/books/{b1['id']}", json={"name": "New Name", "is_active": True})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"
    assert r.json()["is_active"] is True

    active = client.get("/api/books/active").json()
    assert active["id"] == b1["id"]


def test_expenses_are_filed_under_active_book_and_totalled():
    book = client.post("/api/books", json={"name": "Grocery Run"}).json()
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    client.post("/api/expenses", json={"raw_text": "petrol 500"})

    books = client.get("/api/books").json()
    this_book = next(b for b in books if b["id"] == book["id"])
    assert this_book["count"] == 2
    assert float(this_book["total"]) == 520.0

    filtered = client.get("/api/expenses", params={"book_id": book["id"]}).json()
    assert len(filtered) == 2


def test_delete_book_cascades_to_its_expenses():
    book = client.post("/api/books", json={"name": "Temp Trip"}).json()
    client.post("/api/expenses", json={"raw_text": "tea 20"})

    r = client.delete(f"/api/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["deleted_expenses"] == 1

    assert client.get("/api/expenses", params={"book_id": book["id"]}).json() == []


def test_deleting_active_book_falls_back_to_another_existing_book():
    """Regression: deleting the currently active book must not leave the
    app with no active book while other valid books still exist — that
    would wrongly force the create-a-book prompt again."""
    client.post("/api/books", json={"name": "Keeper"}).json()
    active = client.post("/api/books", json={"name": "To Delete"}).json()
    assert active["is_active"] is True

    client.delete(f"/api/books/{active['id']}")

    new_active = client.get("/api/books/active")
    assert new_active.status_code == 200
    assert new_active.json()["name"] == "Keeper"


def test_deleting_the_only_book_leaves_no_active_book():
    for b in client.get("/api/books").json():
        client.delete(f"/api/books/{b['id']}")

    only = client.post("/api/books", json={"name": "Only One"}).json()
    client.delete(f"/api/books/{only['id']}")

    assert client.get("/api/books/active").status_code == 404

    # restore a book so the autouse fixture's next setup is unaffected
    client.post("/api/books", json={"name": "Test Book"})


def test_delete_missing_book_404():
    r = client.delete("/api/books/999999")
    assert r.status_code == 404


def test_add_expense_without_any_book_returns_409():
    """Regression: creating an expense before any book exists must fail
    loudly, not silently attach to nothing."""
    for b in client.get("/api/books").json():
        client.delete(f"/api/books/{b['id']}")

    r = client.post("/api/expenses", json={"raw_text": "tea 20"})
    assert r.status_code == 409

    # restore a book so the autouse fixture's teardown/next setup is unaffected
    client.post("/api/books", json={"name": "Test Book"})


# ═══════════════════════════════════════════════
# Add expense — the reported "goes to pending" bug
# ═══════════════════════════════════════════════
def test_add_expense_raw_text_succeeds():
    r = client.post("/api/expenses", json={"raw_text": "tea 20"})
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == "20.00"
    assert body["intent"] == "tea_snacks"


def test_add_expense_uses_the_category_the_user_picked():
    """The user chooses the category from a dropdown — it must win over the
    auto-detected one ('tea' would otherwise be tea_snacks)."""
    r = client.post("/api/expenses", json={"raw_text": "tea 20", "intent": "food"})
    assert r.status_code == 201
    body = r.json()
    assert body["intent"] == "food"
    assert body["amount"] == "20.00"
    assert body["is_manual_override"] is True


def test_add_expense_with_unknown_category_returns_400():
    r = client.post("/api/expenses", json={"raw_text": "tea 20", "intent": "nope"})
    assert r.status_code == 400


def test_add_expense_without_category_still_auto_detects():
    r = client.post("/api/expenses", json={"raw_text": "petrol 500"})
    assert r.status_code == 201
    assert r.json()["intent"] == "petrol"


def test_add_expense_manual_fields():
    r = client.post(
        "/api/expenses",
        json={"amount": 100, "intent": "food", "description": "lunch"},
    )
    assert r.status_code == 201
    assert r.json()["intent"] == "food"


def test_add_expense_no_amount_returns_422_not_silent_failure():
    """Text with no amount must fail loudly (422) so the client can show
    a real error instead of mis-classifying it as 'offline, queued'."""
    r = client.post("/api/expenses", json={"raw_text": "just some words"})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_add_expense_empty_body_returns_422():
    r = client.post("/api/expenses", json={})
    assert r.status_code == 422


def test_add_expense_unknown_intent_returns_400():
    r = client.post(
        "/api/expenses",
        json={"amount": 50, "intent": "not_a_real_intent", "description": "x"},
    )
    assert r.status_code == 400


# ═══════════════════════════════════════════════
# List / get / filter
# ═══════════════════════════════════════════════
def test_list_and_get_expense():
    created = client.post("/api/expenses", json={"raw_text": "petrol 500"}).json()
    r = client.get("/api/expenses")
    assert r.status_code == 200
    assert any(e["id"] == created["id"] for e in r.json())

    r2 = client.get(f"/api/expenses/{created['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == created["id"]


def test_get_missing_expense_404():
    r = client.get("/api/expenses/999999")
    assert r.status_code == 404


def test_filter_by_intent():
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    client.post("/api/expenses", json={"raw_text": "petrol 500"})
    r = client.get("/api/expenses", params={"intent": "petrol"})
    assert r.status_code == 200
    assert all(e["intent"] == "petrol" for e in r.json())


# ═══════════════════════════════════════════════
# Preview (live classification, no save)
# ═══════════════════════════════════════════════
def test_preview_does_not_create_expense():
    before = len(client.get("/api/expenses").json())
    r = client.post("/api/preview", json={"raw_text": "coffee 45"})
    assert r.status_code == 200
    assert r.json()["intent"] == "tea_snacks"
    after = len(client.get("/api/expenses").json())
    assert before == after


# ═══════════════════════════════════════════════
# Update + self-learning
# ═══════════════════════════════════════════════
def test_update_expense_amount_and_description():
    created = client.post("/api/expenses", json={"raw_text": "tea 20"}).json()
    r = client.patch(f"/api/expenses/{created['id']}", json={"amount": 30})
    assert r.status_code == 200
    assert r.json()["amount"] == "30.00"


def test_update_intent_triggers_learning():
    created = client.post(
        "/api/expenses", json={"raw_text": "xyzzyplugh 40"}
    ).json()
    assert created["intent"] == "others"

    r = client.patch(f"/api/expenses/{created['id']}", json={"intent": "grocery"})
    assert r.status_code == 200
    assert r.json()["intent"] == "grocery"
    assert r.json()["is_manual_override"] is True

    kws = client.get("/api/keywords").json()
    assert any(k["intent"] == "grocery" for k in kws)

    # Next time the same word is used, the learned keyword should win.
    r2 = client.post("/api/expenses", json={"raw_text": "xyzzyplugh 40"})
    assert r2.json()["intent"] == "grocery"


def test_update_missing_expense_404():
    r = client.patch("/api/expenses/999999", json={"amount": 5})
    assert r.status_code == 404


# ═══════════════════════════════════════════════
# Delete — single + delete-all, and disk space reclaim
# ═══════════════════════════════════════════════
def test_delete_single_expense():
    created = client.post("/api/expenses", json={"raw_text": "tea 20"}).json()
    r = client.delete(f"/api/expenses/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/expenses/{created['id']}").status_code == 404


def test_delete_missing_expense_404():
    r = client.delete("/api/expenses/999999")
    assert r.status_code == 404


def test_delete_all_expenses_returns_count_and_empties_list():
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    client.post("/api/expenses", json={"raw_text": "petrol 500"})
    client.post("/api/expenses", json={"raw_text": "movie ticket 250"})

    r = client.delete("/api/expenses")
    assert r.status_code == 200
    assert r.json()["deleted"] == 3
    assert client.get("/api/expenses").json() == []


# ═══════════════════════════════════════════════
# Budgets
# ═══════════════════════════════════════════════
def test_set_and_get_budget():
    r = client.post("/api/budgets", json={"intent": "food", "monthly_limit": 3000})
    assert r.status_code == 201
    budgets = client.get("/api/budgets").json()
    assert any(b["intent"] == "food" and b["monthly_limit"] == "3000.00" for b in budgets)


# ═══════════════════════════════════════════════
# Keywords
# ═══════════════════════════════════════════════
def test_delete_single_keyword():
    created = client.post("/api/expenses", json={"raw_text": "zorbnax 40"}).json()
    client.patch(f"/api/expenses/{created['id']}", json={"intent": "medical"})
    kws = client.get("/api/keywords").json()
    assert len(kws) > 0
    kw = kws[0]["keyword"]
    r = client.delete(f"/api/keywords/{kw}")
    assert r.status_code == 204
    assert kw not in [k["keyword"] for k in client.get("/api/keywords").json()]


def test_clear_all_keywords():
    created = client.post("/api/expenses", json={"raw_text": "zorbnax 40"}).json()
    client.patch(f"/api/expenses/{created['id']}", json={"intent": "medical"})
    r = client.delete("/api/keywords")
    assert r.status_code == 200
    assert client.get("/api/keywords").json() == []


# ═══════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════
def test_monthly_summary_totals():
    from datetime import date
    month = date.today().strftime("%Y-%m")
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    client.post("/api/expenses", json={"raw_text": "petrol 500"})

    r = client.get("/api/summary", params={"month": month})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert float(body["total"]) == 520.0


def test_summary_scoped_to_book_ignores_other_books():
    """Regression: the summary endpoint must not silently mix expenses from
    other books into a book-scoped view (this leaked in the initial books
    implementation — Summary showed calendar-month totals across every book)."""
    book_a = client.post("/api/books", json={"name": "Book A"}).json()
    client.post("/api/expenses", json={"raw_text": "tea 20"})

    book_b = client.post("/api/books", json={"name": "Book B"}).json()
    client.post("/api/expenses", json={"raw_text": "petrol 500"})

    summary_a = client.get("/api/summary", params={"book_id": book_a["id"]}).json()
    assert summary_a["count"] == 1
    assert float(summary_a["total"]) == 20.0

    summary_b = client.get("/api/summary", params={"book_id": book_b["id"]}).json()
    assert summary_b["count"] == 1
    assert float(summary_b["total"]) == 500.0


# ═══════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════
def test_export_json_and_csv():
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    r_json = client.get("/api/export/json")
    assert r_json.status_code == 200
    assert len(r_json.json()) == 1

    r_csv = client.get("/api/export/csv")
    assert r_csv.status_code == 200
    assert "raw_text" in r_csv.text


def test_export_includes_book_id_and_name():
    book = client.post("/api/books", json={"name": "Export Test Book"}).json()
    client.post("/api/expenses", json={"raw_text": "tea 20"})

    r = client.get("/api/export/json")
    assert r.status_code == 200
    row = next(e for e in r.json() if e["description"] == "Tea")
    assert row["book_id"] == book["id"]
    assert row["book_name"] == "Export Test Book"


def test_export_can_filter_by_book():
    book_a = client.post("/api/books", json={"name": "Export A"}).json()
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    client.post("/api/books", json={"name": "Export B"})
    client.post("/api/expenses", json={"raw_text": "petrol 500"})

    r = client.get("/api/export/json", params={"book_id": book_a["id"]})
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["description"] == "Tea"


def test_export_json_does_not_crash_on_decimal_confidence():
    """Regression: confidence is stored as SQL NUMERIC and comes back as a
    Decimal, which the stdlib json encoder can't serialize directly."""
    client.post("/api/expenses", json={"raw_text": "tea 20"})
    r = client.get("/api/export/json")
    assert r.status_code == 200
    assert isinstance(r.json()[0]["confidence"], float)
