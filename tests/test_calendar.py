# tests/test_calendar.py
from datetime import datetime, timedelta, date

from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
from simledge.recurring import check_bill_paid, calendar_bills


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


def test_check_bill_paid_found(tmp_path):
    conn = _setup_db(tmp_path)
    upsert_transaction(conn, "t1", "acct-1", "2026-03-15", -50.00, "TEST_BILL")
    result = check_bill_paid(conn, "TEST_BILL", -50.00, "2026-03-15")
    assert result["paid"] is True
    assert result["actual_date"] == "2026-03-15"
    assert result["actual_amount"] == -50.00
    conn.close()


def test_check_bill_paid_not_found(tmp_path):
    conn = _setup_db(tmp_path)
    result = check_bill_paid(conn, "TEST_NONEXISTENT", -50.00, "2026-03-15")
    assert result["paid"] is False
    assert result["actual_date"] is None
    assert result["actual_amount"] is None
    conn.close()


def test_check_bill_paid_amount_tolerance(tmp_path):
    conn = _setup_db(tmp_path)
    # Amount within 10% tolerance: -50 vs -52 (4% difference)
    upsert_transaction(conn, "t1", "acct-1", "2026-03-15", -52.00, "TEST_BILL")
    result = check_bill_paid(conn, "TEST_BILL", -50.00, "2026-03-15")
    assert result["paid"] is True
    assert result["actual_amount"] == -52.00
    conn.close()


def test_check_bill_paid_date_tolerance(tmp_path):
    conn = _setup_db(tmp_path)
    # Transaction 3 days off from expected
    upsert_transaction(conn, "t1", "acct-1", "2026-03-18", -50.00, "TEST_BILL")
    result = check_bill_paid(conn, "TEST_BILL", -50.00, "2026-03-15")
    assert result["paid"] is True
    assert result["actual_date"] == "2026-03-18"
    conn.close()


def test_calendar_bills_mixed_status(tmp_path):
    conn = _setup_db(tmp_path)
    today = date.today()
    # Create monthly recurring with 4 occurrences starting 4 months ago
    start = (today - timedelta(days=120)).strftime("%Y-%m-%d")
    _insert_recurring(conn, "TEST_SUB", -15.00, start, 30, 4)

    # Get current month's calendar
    month = today.strftime("%Y-%m")
    bills = calendar_bills(conn, month)

    # We should get results (may be 0 or 1 depending on timing)
    assert isinstance(bills, list)
    # Each bill should have required fields
    for b in bills:
        assert b["status"] in ("paid", "upcoming", "overdue")
        assert "date" in b
        assert "day" in b
        assert "weekday" in b
        assert "description" in b
        assert "expected_amount" in b
        assert "account" in b
    conn.close()


def test_calendar_bills_empty_month(tmp_path):
    conn = _setup_db(tmp_path)
    # No recurring transactions → empty list
    bills = calendar_bills(conn, "2026-03")
    assert bills == []
    conn.close()
