# tests/test_watchlist.py
import pytest
from unittest.mock import patch
from datetime import date

from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction


def _seed_db(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")

    # Food transactions
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -25.00, "STARBUCKS", category="Food:Coffee")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-05", -30.00, "STARBUCKS", category="Food:Coffee")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-10", -50.00, "WHOLE FOODS", category="Food:Groceries")

    # Amazon transactions
    upsert_transaction(conn, "t4", "acct-1", "2026-03-02", -100.00, "AMAZON PURCHASE", category="Shopping")
    upsert_transaction(conn, "t5", "acct-1", "2026-03-08", -75.00, "AMAZON PRIME", category="Shopping")

    # Income
    upsert_transaction(conn, "t6", "acct-1", "2026-03-01", 5000.00, "PAYROLL", category="Income")

    return conn


def test_create_watchlist(tmp_path):
    from simledge.watchlist import create_watchlist, get_watchlists
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Coffee", monthly_target=100.00, filter_category="Food:Coffee")
    watchlists = get_watchlists(conn)
    assert len(watchlists) == 1
    assert watchlists[0]["name"] == "Coffee"
    assert watchlists[0]["monthly_target"] == 100.00
    assert watchlists[0]["filter_category"] == "Food:Coffee"
    assert watchlists[0]["id"] == wl_id
    conn.close()


def test_create_watchlist_validation(tmp_path):
    from simledge.watchlist import create_watchlist
    conn = _seed_db(tmp_path)

    with pytest.raises(ValueError, match="at least one filter"):
        create_watchlist(conn, "Bad Watchlist")
    conn.close()


def test_watchlist_spending_category(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Coffee", monthly_target=100.00, filter_category="Food:Coffee")
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    assert result["actual"] == 55.00
    assert result["transaction_count"] == 2
    assert result["monthly_target"] == 100.00
    conn.close()


def test_watchlist_spending_description(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Amazon", filter_description="%amazon%")
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    assert result["actual"] == 175.00
    assert result["transaction_count"] == 2
    conn.close()


def test_watchlist_spending_tag(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    # Create a tag and tag a transaction
    conn.execute("INSERT INTO tags (name) VALUES ('vacation')")
    conn.execute(
        "INSERT INTO transaction_tags (transaction_id, tag_id) VALUES ('t4', 1)"
    )
    conn.commit()

    wl_id = create_watchlist(conn, "Vacation", filter_tag="vacation")
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    assert result["actual"] == 100.00
    assert result["transaction_count"] == 1
    conn.close()


def test_watchlist_spending_combined(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    # Category + description filter AND'd: only STARBUCKS under Food:Coffee
    wl_id = create_watchlist(
        conn, "Starbucks Coffee",
        filter_category="Food:Coffee",
        filter_description="%starbucks%",
    )
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    assert result["actual"] == 55.00
    assert result["transaction_count"] == 2
    conn.close()


def test_watchlist_spending_with_target(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Coffee", monthly_target=100.00, filter_category="Food:Coffee")
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    assert result["pct_used"] == 55.0
    assert result["remaining"] == 45.00
    conn.close()


def test_watchlist_spending_no_target(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Amazon", filter_description="%amazon%")
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    assert result["remaining"] is None
    assert result["pct_used"] is None
    assert result["on_track"] is None
    conn.close()


def test_watchlist_projected(tmp_path):
    from simledge.watchlist import create_watchlist, watchlist_spending
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Coffee", monthly_target=100.00, filter_category="Food:Coffee")
    # On day 15 of 31-day month, spent $55 -> projected ~55 * 31/15 = ~113.67
    with patch("simledge.watchlist.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 15)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        result = watchlist_spending(conn, wl_id, "2026-03")

    expected_projected = 55.00 * (31 / 15)
    assert abs(result["projected_month_end"] - expected_projected) < 0.01
    assert result["on_track"] is False  # projected > target
    conn.close()


def test_delete_watchlist(tmp_path):
    from simledge.watchlist import create_watchlist, get_watchlists, delete_watchlist
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Coffee", filter_category="Food:Coffee")
    assert len(get_watchlists(conn)) == 1

    delete_watchlist(conn, wl_id)
    assert len(get_watchlists(conn)) == 0
    conn.close()


def test_update_watchlist(tmp_path):
    from simledge.watchlist import create_watchlist, get_watchlists, update_watchlist
    conn = _seed_db(tmp_path)

    wl_id = create_watchlist(conn, "Coffee", monthly_target=100.00, filter_category="Food:Coffee")

    update_watchlist(conn, wl_id, monthly_target=200.00, filter_description="%starbucks%")
    watchlists = get_watchlists(conn)
    assert watchlists[0]["monthly_target"] == 200.00
    assert watchlists[0]["filter_description"] == "%starbucks%"
    assert watchlists[0]["filter_category"] == "Food:Coffee"  # unchanged
    conn.close()
