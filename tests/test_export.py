# tests/test_export.py
from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction


def _seed(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(
        conn, "t1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", category="groceries"
    )
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -23.99, "AMAZON", category="shopping")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-01", 4225.00, "PAYROLL", category="income")
    return conn


def _seed_multi_account(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_institution(conn, "org-2", "Amex", "amex.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-2", "org-2", "Platinum", "USD", "credit")
    for i in range(10):
        upsert_transaction(
            conn, f"t-a1-{i}", "acct-1", f"2026-03-{i + 1:02d}", -10.00, f"STORE_{i}"
        )
    for i in range(5):
        upsert_transaction(conn, f"t-a2-{i}", "acct-2", f"2026-03-{i + 1:02d}", -20.00, f"SHOP_{i}")
    upsert_transaction(
        conn, "t-inc", "acct-1", "2026-03-01", 5000.00, "PAYROLL", category="Income:Salary"
    )
    return conn


def test_export_markdown(tmp_path):
    from simledge.export import export_markdown

    conn = _seed(tmp_path)
    output = export_markdown(conn, "2026-03")
    assert "## SimpLedge Export" in output
    assert "WHOLE FOODS" in output
    assert "groceries" in output
    assert "| Date" in output  # table header
    conn.close()


def test_export_csv(tmp_path):
    from simledge.export import export_csv

    conn = _seed(tmp_path)
    output = export_csv(conn, "2026-03")
    lines = output.strip().split("\n")
    assert "date" in lines[0].lower()  # header row
    assert len(lines) >= 4  # header + 3 transactions
    conn.close()


def test_export_json(tmp_path):
    import json

    from simledge.export import export_json

    conn = _seed(tmp_path)
    output = export_json(conn, "2026-03")
    data = json.loads(output)
    assert "transactions" in data
    assert len(data["transactions"]) == 3
    conn.close()


# --- Comprehensive export tests ---


def test_export_json_full_all_sections(tmp_path):
    import json

    from simledge.export import ALL_SECTIONS, export_json_full

    conn = _seed(tmp_path)
    output = export_json_full(conn, "2026-03")
    data = json.loads(output)

    assert "meta" in data
    assert data["meta"]["month"] == "2026-03"
    assert data["meta"]["sections"] == ALL_SECTIONS

    # Core sections present
    assert "summary" in data
    assert "spending" in data
    assert "transactions" in data
    assert "accounts" in data

    # Summary values make sense
    assert data["summary"]["total_spending"] < 0
    assert data["summary"]["total_income"] == 4225.0  # category="income" matches LIKE 'Income%'
    assert "daily_average_spending" in data["summary"]
    assert "uncategorized_count" in data["summary"]

    # Spending breakdown present
    assert "by_category" in data["spending"]
    assert "top_merchants" in data["spending"]

    # Transactions has metadata
    assert data["transactions"]["total_count"] == 3
    assert len(data["transactions"]["items"]) == 3
    assert data["transactions"]["truncated"] is False
    conn.close()


def test_export_json_full_single_section(tmp_path):
    import json

    from simledge.export import export_json_full

    conn = _seed(tmp_path)
    output = export_json_full(conn, "2026-03", sections=["summary"])
    data = json.loads(output)

    assert "meta" in data
    assert data["meta"]["sections"] == ["summary"]
    assert "summary" in data
    # Other sections not present
    assert "transactions" not in data
    assert "spending" not in data
    assert "accounts" not in data
    conn.close()


def test_export_json_full_transaction_limit(tmp_path):
    import json

    from simledge.export import export_json_full

    conn = _seed_multi_account(tmp_path)
    output = export_json_full(conn, "2026-03", sections=["transactions"], limit=3)
    data = json.loads(output)

    txns = data["transactions"]
    assert txns["total_count"] == 16  # 10 + 5 + 1
    assert txns["returned_count"] == 3
    assert txns["limit"] == 3
    assert txns["truncated"] is True
    assert len(txns["items"]) == 3
    conn.close()


def test_export_json_full_account_filter(tmp_path):
    import json

    from simledge.export import export_json_full

    conn = _seed_multi_account(tmp_path)
    output = export_json_full(
        conn, "2026-03", sections=["transactions", "summary"], account_ids={"acct-2"}
    )
    data = json.loads(output)

    assert data["meta"]["account_filter"] == ["acct-2"]
    # Only acct-2 transactions (5 SHOP_*)
    assert data["transactions"]["total_count"] == 5
    for item in data["transactions"]["items"]:
        assert item["account"] == "Platinum"
    conn.close()


def test_export_json_full_empty_db(tmp_path):
    import json

    from simledge.export import export_json_full

    conn = init_db(str(tmp_path / "empty.db"))
    output = export_json_full(conn, "2026-03")
    data = json.loads(output)

    assert "meta" in data
    assert data["summary"]["total_spending"] == 0
    assert data["summary"]["total_income"] == 0
    assert data["transactions"]["total_count"] == 0
    assert data["transactions"]["items"] == []
    conn.close()


def test_export_json_full_is_valid_json(tmp_path):
    import json

    from simledge.export import export_json_full

    conn = _seed(tmp_path)
    output = export_json_full(conn, "2026-03")
    # Should not raise
    data = json.loads(output)
    assert isinstance(data, dict)
    conn.close()


def test_export_backward_compat(tmp_path):
    """Existing export_json returns the old format unchanged."""
    import json

    from simledge.export import export_json

    conn = _seed(tmp_path)
    output = export_json(conn, "2026-03")
    data = json.loads(output)

    # Old format: flat keys
    assert "month" in data
    assert "summary" in data
    assert "categories" in data
    assert "transactions" in data
    assert isinstance(data["transactions"], list)
    # No meta block
    assert "meta" not in data
    conn.close()


def test_get_transactions_with_limit(tmp_path):
    from simledge.export import _get_transactions

    conn = _seed_multi_account(tmp_path)
    txns = _get_transactions(conn, "2026-03", limit=5)
    assert len(txns) == 5
    conn.close()


def test_get_transactions_no_limit(tmp_path):
    from simledge.export import _get_transactions

    conn = _seed_multi_account(tmp_path)
    txns = _get_transactions(conn, "2026-03")
    assert len(txns) == 16  # all transactions
    conn.close()


def test_export_markdown_full_all_sections(tmp_path):
    from simledge.export import export_markdown_full

    conn = _seed(tmp_path)
    output = export_markdown_full(conn, "2026-03")

    # Has comprehensive sections
    assert "# SimpLedge Export" in output
    assert "## Summary" in output
    assert "Daily average spending" in output
    assert "Uncategorized" in output
    assert "## Spending by Category" in output
    assert "## Transactions" in output
    assert "WHOLE FOODS" in output
    conn.close()


def test_export_markdown_full_single_section(tmp_path):
    from simledge.export import export_markdown_full

    conn = _seed(tmp_path)
    output = export_markdown_full(conn, "2026-03", sections=["summary"])

    assert "## Summary" in output
    # No transactions section
    assert "## Transactions" not in output
    assert "## Spending by Category" not in output
    conn.close()


def test_export_csv_full(tmp_path):
    from simledge.export import export_csv_full

    conn = _seed_multi_account(tmp_path)
    output = export_csv_full(conn, "2026-03", limit=5)
    lines = output.strip().split("\n")
    assert "date" in lines[0].lower()
    assert len(lines) == 6  # header + 5 rows
    conn.close()
