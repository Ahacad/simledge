# tests/test_budget.py
from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction


def _seed_db(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-2", "org-1", "Credit Card", "USD", "credit")

    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", category="Groceries")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -23.99, "AMAZON", category="Shopping")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-01", 4225.00, "PAYROLL", category="Income")
    upsert_transaction(conn, "t4", "acct-2", "2026-03-03", -52.10, "SHELL", category="Gas")
    upsert_transaction(conn, "t5", "acct-1", "2026-03-05", -150.00, "RESTAURANT", category="Dining")

    return conn


def test_set_budget(tmp_path):
    from simledge.budget import set_budget, get_budgets
    conn = _seed_db(tmp_path)

    set_budget(conn, "Groceries", 400.00)
    budgets = get_budgets(conn)
    assert len(budgets) == 1
    assert budgets[0]["category"] == "Groceries"
    assert budgets[0]["monthly_limit"] == 400.00

    # Upsert same category
    set_budget(conn, "Groceries", 500.00)
    budgets = get_budgets(conn)
    assert len(budgets) == 1
    assert budgets[0]["monthly_limit"] == 500.00
    conn.close()


def test_get_budgets(tmp_path):
    from simledge.budget import set_budget, get_budgets
    conn = _seed_db(tmp_path)

    set_budget(conn, "Groceries", 400.00)
    set_budget(conn, "Dining", 200.00)
    set_budget(conn, "Gas", 150.00)

    budgets = get_budgets(conn)
    assert len(budgets) == 3
    categories = [b["category"] for b in budgets]
    assert "Groceries" in categories
    assert "Dining" in categories
    assert "Gas" in categories
    conn.close()


def test_delete_budget(tmp_path):
    from simledge.budget import set_budget, get_budgets, delete_budget
    conn = _seed_db(tmp_path)

    set_budget(conn, "Groceries", 400.00)
    budgets = get_budgets(conn)
    assert len(budgets) == 1

    delete_budget(conn, budgets[0]["id"])
    budgets = get_budgets(conn)
    assert len(budgets) == 0
    conn.close()


def test_budget_vs_actual(tmp_path):
    from simledge.budget import set_budget, budget_vs_actual
    conn = _seed_db(tmp_path)

    set_budget(conn, "Groceries", 400.00)
    set_budget(conn, "Dining", 200.00)

    result = budget_vs_actual(conn, "2026-03")
    groceries = next(r for r in result if r["category"] == "Groceries")
    assert groceries["budget"] == 400.00
    assert groceries["actual"] == 47.32
    assert groceries["remaining"] == 400.00 - 47.32
    assert groceries["pct_used"] == round(47.32 / 400.00 * 100, 1)

    dining = next(r for r in result if r["category"] == "Dining")
    assert dining["actual"] == 150.00
    conn.close()


def test_budget_vs_actual_no_spending(tmp_path):
    from simledge.budget import set_budget, budget_vs_actual
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")

    set_budget(conn, "Groceries", 400.00)

    result = budget_vs_actual(conn, "2026-03")
    assert len(result) == 1
    assert result[0]["actual"] == 0
    assert result[0]["pct_used"] == 0
    assert result[0]["remaining"] == 400.00
    conn.close()


def test_total_budget_summary(tmp_path):
    from simledge.budget import set_budget, total_budget_summary
    conn = _seed_db(tmp_path)

    set_budget(conn, "Groceries", 400.00)
    set_budget(conn, "Dining", 200.00)
    set_budget(conn, "Gas", 150.00)

    summary = total_budget_summary(conn, "2026-03")
    assert summary["total_budgeted"] == 750.00
    expected_actual = 47.32 + 150.00 + 52.10  # groceries + dining + gas
    assert abs(summary["total_actual"] - expected_actual) < 0.01
    assert abs(summary["total_remaining"] - (750.00 - expected_actual)) < 0.01

    # Unbudgeted spending: Shopping ($23.99) is not budgeted
    assert abs(summary["unbudgeted_spending"] - 23.99) < 0.01
    conn.close()


def test_budget_vs_actual_with_account_filter(tmp_path):
    from simledge.budget import set_budget, budget_vs_actual
    conn = _seed_db(tmp_path)

    set_budget(conn, "Gas", 150.00)

    # Gas transaction is on acct-2; filtering to acct-1 should show 0 actual
    result = budget_vs_actual(conn, "2026-03", account_ids={"acct-1"})
    gas = next(r for r in result if r["category"] == "Gas")
    assert gas["actual"] == 0

    # Filtering to acct-2 should show the gas charge
    result = budget_vs_actual(conn, "2026-03", account_ids={"acct-2"})
    gas = next(r for r in result if r["category"] == "Gas")
    assert gas["actual"] == 52.10
    conn.close()
