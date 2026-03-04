# tests/test_recurring.py
from datetime import datetime, timedelta

from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
from simledge.recurring import detect_recurring, _normalize_description


def _setup_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    upsert_institution(conn, "bank-1", "Test Bank")
    upsert_account(conn, "acct-1", "bank-1", "Checking", "USD", "checking")
    return conn


def _insert_recurring(conn, desc, amount, start_date, interval_days, count):
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    for i in range(count):
        posted = (dt + timedelta(days=interval_days * i)).strftime("%Y-%m-%d")
        upsert_transaction(
            conn, f"txn-{desc}-{i}", "acct-1", posted, amount, desc
        )


def test_monthly_detection(tmp_path):
    conn = _setup_db(tmp_path)
    _insert_recurring(conn, "TEST_STREAMING", -15.99, "2025-10-01", 30, 4)

    results = detect_recurring(conn)
    assert len(results) == 1
    assert results[0]["frequency"] == "monthly"
    assert results[0]["description"] == "TEST_STREAMING"
    assert results[0]["occurrence_count"] == 4
    conn.close()


def test_weekly_detection(tmp_path):
    conn = _setup_db(tmp_path)
    _insert_recurring(conn, "TEST_GROCERIES", -50.00, "2026-01-01", 7, 5)

    results = detect_recurring(conn)
    assert len(results) == 1
    assert results[0]["frequency"] == "weekly"
    assert results[0]["occurrence_count"] == 5
    conn.close()


def test_random_interval_rejected(tmp_path):
    conn = _setup_db(tmp_path)
    # Irregular intervals: 3, 45, 12 days apart — should not be detected
    dates = ["2026-01-01", "2026-01-04", "2026-02-18", "2026-03-02"]
    for i, d in enumerate(dates):
        upsert_transaction(conn, f"txn-rand-{i}", "acct-1", d, -20.00, "RANDOM_SHOP")

    results = detect_recurring(conn)
    assert len(results) == 0
    conn.close()


def test_amount_tolerance(tmp_path):
    conn = _setup_db(tmp_path)
    # Slightly varying amounts — should still detect as fixed
    amounts = [-100.00, -100.50, -99.80, -100.20]
    dt = datetime(2025, 10, 1)
    for i, amt in enumerate(amounts):
        posted = (dt + timedelta(days=30 * i)).strftime("%Y-%m-%d")
        upsert_transaction(conn, f"txn-vary-{i}", "acct-1", posted, amt, "TEST_UTILITY")

    results = detect_recurring(conn)
    assert len(results) == 1
    assert results[0]["is_fixed_amount"] is True
    conn.close()


def test_normalize_description():
    assert _normalize_description("NETFLIX  #12345") == "netflix"
    assert _normalize_description("  Whole  Foods   ") == "whole foods"
    assert _normalize_description("SPOTIFY USA 00839") == "spotify usa"
    assert _normalize_description("Rent Payment") == "rent payment"
    assert _normalize_description("") == ""
    assert _normalize_description(None) == ""
