# tests/test_analysis.py
from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction, snapshot_balance


def _seed_db(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-2", "org-1", "Credit Card", "USD", "credit")

    # March transactions
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", category="groceries")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -23.99, "AMAZON", category="shopping")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-01", 4225.00, "PAYROLL", category="income")
    upsert_transaction(conn, "t4", "acct-2", "2026-03-03", -52.10, "SHELL", category="gas")

    # February transactions
    upsert_transaction(conn, "t5", "acct-1", "2026-02-15", -60.00, "WHOLE FOODS", category="groceries")
    upsert_transaction(conn, "t6", "acct-1", "2026-02-15", -30.00, "SHELL", category="gas")

    # Balances
    snapshot_balance(conn, "acct-1", "2026-03-01", 4230.50)
    snapshot_balance(conn, "acct-2", "2026-03-01", -1247.30)
    snapshot_balance(conn, "acct-1", "2026-02-01", 3800.00)
    snapshot_balance(conn, "acct-2", "2026-02-01", -1100.00)

    return conn


def test_spending_by_category(tmp_path):
    from simledge.analysis import spending_by_category
    conn = _seed_db(tmp_path)
    result = spending_by_category(conn, "2026-03")
    assert any(r["category"] == "groceries" and r["total"] == -47.32 for r in result)
    assert any(r["category"] == "gas" and r["total"] == -52.10 for r in result)
    conn.close()


def test_monthly_summary(tmp_path):
    from simledge.analysis import monthly_summary
    conn = _seed_db(tmp_path)
    result = monthly_summary(conn, "2026-03")
    assert result["total_spending"] < 0
    assert result["total_income"] > 0
    assert result["net"] == result["total_income"] + result["total_spending"]
    conn.close()


def test_net_worth(tmp_path):
    from simledge.analysis import net_worth_on_date
    conn = _seed_db(tmp_path)
    nw = net_worth_on_date(conn, "2026-03-01")
    assert nw == 4230.50 + (-1247.30)
    conn.close()


def test_spending_trend(tmp_path):
    from simledge.analysis import spending_trend
    conn = _seed_db(tmp_path)
    result = spending_trend(conn, months=2)
    assert len(result) >= 2
    # Each entry has month + total
    assert "month" in result[0]
    assert "total" in result[0]
    conn.close()


def test_monthly_summary_filtered(tmp_path):
    from simledge.analysis import monthly_summary
    conn = _seed_db(tmp_path)
    # Filter to acct-1 only — should exclude the $52.10 gas charge on acct-2
    result = monthly_summary(conn, "2026-03", account_ids={"acct-1"})
    assert result["total_spending"] == -47.32 + -23.99  # groceries + shopping
    assert result["total_income"] == 4225.00
    conn.close()


def test_spending_by_category_filtered(tmp_path):
    from simledge.analysis import spending_by_category
    conn = _seed_db(tmp_path)
    # Filter to acct-2 only — should only have gas
    result = spending_by_category(conn, "2026-03", account_ids={"acct-2"})
    assert len(result) == 1
    assert result[0]["category"] == "gas"
    assert result[0]["total"] == -52.10
    conn.close()


def test_recent_transactions_filtered(tmp_path):
    from simledge.analysis import recent_transactions
    conn = _seed_db(tmp_path)
    # Filter to acct-1 — should not include acct-2 transactions
    result = recent_transactions(conn, limit=50, account_ids={"acct-1"})
    for t in result:
        assert t["account"] == "Checking"
    conn.close()


def test_net_worth_on_date_filtered(tmp_path):
    from simledge.analysis import net_worth_on_date
    conn = _seed_db(tmp_path)
    # Filter to acct-1 only
    nw = net_worth_on_date(conn, "2026-03-01", account_ids={"acct-1"})
    assert nw == 4230.50
    conn.close()


def test_account_summary_filtered(tmp_path):
    from simledge.analysis import account_summary
    conn = _seed_db(tmp_path)
    result = account_summary(conn, account_ids={"acct-2"})
    assert len(result) == 1
    assert result[0]["name"] == "Credit Card"
    conn.close()


# --- Category Hierarchy tests ---

def test_spending_by_category_grouped_flat(tmp_path):
    from simledge.analysis import spending_by_category_grouped
    conn = _seed_db(tmp_path)
    result = spending_by_category_grouped(conn, "2026-03")
    # All categories in _seed_db are flat (no colon)
    for group in result:
        assert group["children"] == []
        assert ":" not in group["category"]
    assert len(result) == 3  # groceries, shopping, gas
    conn.close()


def test_spending_by_category_grouped_hierarchical(tmp_path):
    from simledge.analysis import spending_by_category_grouped
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -100.00, "TEST_GROCERY", category="Food:Groceries")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -50.00, "TEST_DINING", category="Food:Dining")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-03", -30.00, "TEST_SHOP", category="Shopping")
    result = spending_by_category_grouped(conn, "2026-03")
    # Should have 2 groups: Food (with 2 children), Shopping (flat)
    assert len(result) == 2
    food = [g for g in result if g["category"] == "Food"][0]
    assert food["total"] == -150.00
    assert len(food["children"]) == 2
    child_cats = {c["category"] for c in food["children"]}
    assert child_cats == {"Food:Groceries", "Food:Dining"}
    shopping = [g for g in result if g["category"] == "Shopping"][0]
    assert shopping["total"] == -30.00
    assert shopping["children"] == []
    conn.close()


def test_spending_by_category_grouped_single_child(tmp_path):
    from simledge.analysis import spending_by_category_grouped
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -75.00, "TEST_GROCERY", category="Food:Groceries")
    result = spending_by_category_grouped(conn, "2026-03")
    assert len(result) == 1
    food = result[0]
    assert food["category"] == "Food"
    assert food["total"] == -75.00
    assert len(food["children"]) == 1
    assert food["children"][0]["category"] == "Food:Groceries"
    conn.close()


def test_spending_by_category_grouped_empty(tmp_path):
    from simledge.analysis import spending_by_category_grouped
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    result = spending_by_category_grouped(conn, "2026-03")
    assert result == []
    conn.close()


# --- Income Report tests ---

def test_income_by_category(tmp_path):
    from simledge.analysis import income_by_category
    conn = _seed_db(tmp_path)
    result = income_by_category(conn, "2026-03")
    assert len(result) == 1
    assert result[0]["category"] == "income"
    assert result[0]["total"] == 4225.00
    conn.close()


def test_income_by_category_empty(tmp_path):
    from simledge.analysis import income_by_category
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    result = income_by_category(conn, "2026-03")
    assert result == []
    conn.close()


def test_income_trend(tmp_path):
    from simledge.analysis import income_trend
    conn = _seed_db(tmp_path)
    # Add income in February too
    upsert_transaction(conn, "t7", "acct-1", "2026-02-01", 4100.00, "PAYROLL", category="income")
    result = income_trend(conn, months=2)
    assert len(result) >= 2
    assert "month" in result[0]
    assert "total" in result[0]
    # Feb income should be 4100, March should be 4225
    feb = [r for r in result if r["month"] == "2026-02"]
    mar = [r for r in result if r["month"] == "2026-03"]
    assert len(feb) == 1 and feb[0]["total"] == 4100.00
    assert len(mar) == 1 and mar[0]["total"] == 4225.00
    conn.close()


def test_income_by_category_filtered(tmp_path):
    from simledge.analysis import income_by_category
    conn = _seed_db(tmp_path)
    # acct-2 has no income — filter to it
    result = income_by_category(conn, "2026-03", account_ids={"acct-2"})
    assert result == []
    # acct-1 has the payroll
    result = income_by_category(conn, "2026-03", account_ids={"acct-1"})
    assert len(result) == 1
    assert result[0]["total"] == 4225.00
    conn.close()


# --- Year-over-Year tests ---

def _seed_yoy_db(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")

    # March 2026 transactions
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -100.00, "TEST_GROCERY", category="groceries")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -50.00, "TEST_SHOP", category="shopping")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-01", 5000.00, "TEST_PAYROLL", category="income")

    # March 2025 transactions (same month, previous year)
    upsert_transaction(conn, "t4", "acct-1", "2025-03-01", -120.00, "TEST_GROCERY", category="groceries")
    upsert_transaction(conn, "t5", "acct-1", "2025-03-02", -80.00, "TEST_SHOP", category="shopping")
    upsert_transaction(conn, "t6", "acct-1", "2025-03-01", 4500.00, "TEST_PAYROLL", category="income")

    return conn


def test_yoy_comparison(tmp_path):
    from simledge.analysis import yoy_comparison
    conn = _seed_yoy_db(tmp_path)
    result = yoy_comparison(conn, "2026-03")
    assert result["current_month"] == "2026-03"
    assert result["previous_month"] == "2025-03"
    assert result["current_spending"] == -150.00
    assert result["previous_spending"] == -200.00
    # Spending decreased: (150 - 200) / 200 * 100 = -25%
    assert result["spending_change_pct"] == -25.0
    # Income increased: (5000 - 4500) / 4500 * 100 ≈ 11.1%
    assert abs(result["income_change_pct"] - 11.111) < 0.1
    conn.close()


def test_yoy_comparison_no_previous_data(tmp_path):
    from simledge.analysis import yoy_comparison
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -100.00, "TEST_MERCHANT", category="groceries")
    result = yoy_comparison(conn, "2026-03")
    assert result["previous_spending"] == 0
    assert result["spending_change_pct"] is None
    assert result["previous_income"] == 0
    assert result["income_change_pct"] is None
    conn.close()


def test_yoy_comparison_category_new(tmp_path):
    from simledge.analysis import yoy_comparison
    conn = _seed_yoy_db(tmp_path)
    # Add a category that only exists in 2026
    upsert_transaction(conn, "t7", "acct-1", "2026-03-05", -30.00, "TEST_GAS", category="gas")
    result = yoy_comparison(conn, "2026-03")
    gas = [c for c in result["categories"] if c["category"] == "gas"]
    assert len(gas) == 1
    assert gas[0]["current"] == -30.00
    assert gas[0]["previous"] == 0
    assert gas[0]["change_pct"] is None
    conn.close()


def test_yoy_comparison_category_gone(tmp_path):
    from simledge.analysis import yoy_comparison
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    # Category only in 2025
    upsert_transaction(conn, "t1", "acct-1", "2025-03-01", -75.00, "TEST_GYM", category="fitness")
    # Different category in 2026
    upsert_transaction(conn, "t2", "acct-1", "2026-03-01", -50.00, "TEST_SHOP", category="shopping")
    result = yoy_comparison(conn, "2026-03")
    fitness = [c for c in result["categories"] if c["category"] == "fitness"]
    assert len(fitness) == 1
    assert fitness[0]["current"] == 0
    assert fitness[0]["previous"] == -75.00
    conn.close()


def test_ytd_comparison(tmp_path):
    from simledge.analysis import ytd_comparison
    from unittest.mock import patch
    from datetime import datetime as dt
    conn = _seed_yoy_db(tmp_path)
    # Add Jan + Feb data for both years
    upsert_transaction(conn, "t10", "acct-1", "2026-01-15", -200.00, "TEST_JAN", category="groceries")
    upsert_transaction(conn, "t11", "acct-1", "2026-02-15", -180.00, "TEST_FEB", category="groceries")
    upsert_transaction(conn, "t12", "acct-1", "2025-01-15", -220.00, "TEST_JAN", category="groceries")
    upsert_transaction(conn, "t13", "acct-1", "2025-02-15", -190.00, "TEST_FEB", category="groceries")
    # Mock datetime.now() to March 2026
    mock_now = dt(2026, 3, 15)
    with patch("simledge.analysis.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *a, **kw: dt(*a, **kw)
        result = ytd_comparison(conn)
    assert result["current_year"] == "2026"
    assert result["months_counted"] == 3
    # 2026 YTD spending: -200 + -180 + -100 + -50 = -530
    assert result["current_spending"] == -530.00
    # 2025 YTD spending: -220 + -190 + -120 + -80 = -610
    assert result["previous_spending"] == -610.00
    conn.close()


def test_ytd_comparison_first_year(tmp_path):
    from simledge.analysis import ytd_comparison
    from unittest.mock import patch
    from datetime import datetime as dt
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -100.00, "TEST_MERCHANT", category="groceries")
    mock_now = dt(2026, 3, 15)
    with patch("simledge.analysis.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *a, **kw: dt(*a, **kw)
        result = ytd_comparison(conn)
    assert result["previous_spending"] == 0
    assert result["spending_change_pct"] is None
    assert result["previous_income"] == 0
    assert result["income_change_pct"] is None
    conn.close()
