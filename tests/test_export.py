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
