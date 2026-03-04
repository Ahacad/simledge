# tests/test_cashflow.py
from datetime import date, timedelta

from simledge.cashflow import project_balances
from simledge.db import (
    init_db,
    snapshot_balance,
    upsert_account,
    upsert_institution,
    upsert_transaction,
)
from simledge.recurring import generate_occurrences


def _setup_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    upsert_institution(conn, "bank-1", "Test Bank")
    upsert_account(conn, "acct-1", "bank-1", "Checking", "USD", "checking")
    return conn


def _insert_recurring(conn, desc, amount, start_date, interval_days, count):
    from datetime import datetime
    from datetime import timedelta as td

    dt = datetime.strptime(start_date, "%Y-%m-%d")
    for i in range(count):
        posted = (dt + td(days=interval_days * i)).strftime("%Y-%m-%d")
        upsert_transaction(conn, f"txn-{desc}-{i}", "acct-1", posted, amount, desc)


# --- generate_occurrences tests ---


def test_generate_occurrences_monthly():
    today = date.today()
    item = {
        "description": "TEST_RENT",
        "frequency": "monthly",
        "last_amount": -2000.00,
        "next_expected": today.strftime("%Y-%m-%d"),
        "account": "Checking",
    }
    occs = generate_occurrences(item, today, today + timedelta(days=90))
    # Monthly (30-day interval) over 90 days: day 0, day 30, day 60, day 90 → 4 occurrences
    assert len(occs) >= 3
    assert all(o["amount"] == -2000.00 for o in occs)
    assert all(o["description"] == "TEST_RENT" for o in occs)
    assert all(o["account"] == "Checking" for o in occs)


def test_generate_occurrences_weekly():
    today = date.today()
    item = {
        "description": "TEST_GROCERIES",
        "frequency": "weekly",
        "last_amount": -50.00,
        "next_expected": today.strftime("%Y-%m-%d"),
        "account": "Checking",
    }
    occs = generate_occurrences(item, today, today + timedelta(days=30))
    # Weekly (7-day interval) over 30 days: ~4-5 occurrences
    assert len(occs) >= 4
    assert all(o["amount"] == -50.00 for o in occs)


def test_generate_occurrences_empty_window():
    today = date.today()
    item = {
        "description": "TEST_FUTURE",
        "frequency": "monthly",
        "last_amount": -100.00,
        "next_expected": (today + timedelta(days=100)).strftime("%Y-%m-%d"),
        "account": "Checking",
    }
    occs = generate_occurrences(item, today, today + timedelta(days=30))
    assert occs == []


# --- project_balances tests ---


def test_project_balances_basic(tmp_path):
    conn = _setup_db(tmp_path)
    snapshot_balance(conn, "acct-1", date.today().strftime("%Y-%m-%d"), 1000.00)
    # Insert 4 monthly recurring debits so detect_recurring picks it up
    start = (date.today() - timedelta(days=120)).strftime("%Y-%m-%d")
    _insert_recurring(conn, "TEST_BILL", -100.00, start, 30, 4)

    result = project_balances(conn, days=90)
    summary = result["summary"]
    # Balance should decrease over time
    assert summary["projected_90d"] < summary["current_total"]
    assert len(result["daily_totals"]) == 91  # 0..90 inclusive
    conn.close()


def test_project_balances_income_and_spending(tmp_path):
    conn = _setup_db(tmp_path)
    snapshot_balance(conn, "acct-1", date.today().strftime("%Y-%m-%d"), 5000.00)
    start = (date.today() - timedelta(days=120)).strftime("%Y-%m-%d")
    _insert_recurring(conn, "TEST_SALARY", 3000.00, start, 30, 4)
    _insert_recurring(conn, "TEST_RENT", -2000.00, start, 30, 4)

    result = project_balances(conn, days=90)
    summary = result["summary"]
    # Net +1000/month, so balance should increase
    assert summary["projected_90d"] > summary["current_total"]
    conn.close()


def test_negative_balance_detection(tmp_path):
    conn = _setup_db(tmp_path)
    # Low starting balance with large recurring debit
    snapshot_balance(conn, "acct-1", date.today().strftime("%Y-%m-%d"), 150.00)
    start = (date.today() - timedelta(days=120)).strftime("%Y-%m-%d")
    _insert_recurring(conn, "TEST_BIGBILL", -200.00, start, 30, 4)

    result = project_balances(conn, days=90)
    assert len(result["negative_dates"]) > 0
    neg = result["negative_dates"][0]
    assert neg["balance"] < 0
    assert neg["account"] == "Checking"
    conn.close()


def test_negative_balance_ignores_credit_cards(tmp_path):
    """Credit card accounts should not trigger negative balance warnings."""
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    upsert_institution(conn, "bank-1", "Test Bank")
    upsert_account(conn, "acct-1", "bank-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-cc", "bank-1", "Visa Card", "USD", "credit")

    snapshot_balance(conn, "acct-1", date.today().strftime("%Y-%m-%d"), 5000.00)
    snapshot_balance(conn, "acct-cc", date.today().strftime("%Y-%m-%d"), -2000.00)

    result = project_balances(conn, days=30)
    # CC account is negative but should NOT appear in warnings
    for neg in result["negative_dates"]:
        assert neg["account"] != "Visa Card"
    conn.close()


def test_project_balances_no_recurring(tmp_path):
    conn = _setup_db(tmp_path)
    snapshot_balance(conn, "acct-1", date.today().strftime("%Y-%m-%d"), 5000.00)

    result = project_balances(conn, days=90)
    # No recurring → all daily totals should equal current balance
    totals = result["daily_totals"]
    for entry in totals:
        assert entry["projected_balance"] == 5000.00
    conn.close()


def test_project_balances_summary(tmp_path):
    conn = _setup_db(tmp_path)
    snapshot_balance(conn, "acct-1", date.today().strftime("%Y-%m-%d"), 3000.00)
    start = (date.today() - timedelta(days=120)).strftime("%Y-%m-%d")
    _insert_recurring(conn, "TEST_MONTHLY", -100.00, start, 30, 4)

    result = project_balances(conn, days=90)
    summary = result["summary"]
    assert "current_total" in summary
    assert "projected_30d" in summary
    assert "projected_60d" in summary
    assert "projected_90d" in summary
    # 30d should be between current and 90d
    assert summary["projected_30d"] >= summary["projected_90d"]
    assert summary["projected_30d"] <= summary["current_total"]
    conn.close()
