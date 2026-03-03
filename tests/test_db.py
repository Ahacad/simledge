# tests/test_db.py
import sqlite3
import os


def test_init_db_creates_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db
    conn = init_db(db_path)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    assert "institutions" in tables
    assert "accounts" in tables
    assert "balances" in tables
    assert "transactions" in tables
    assert "category_rules" in tables
    assert "sync_log" in tables
    conn.close()


def test_init_db_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db
    conn1 = init_db(db_path)
    conn1.close()
    conn2 = init_db(db_path)
    cursor = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert len(tables) >= 6
    conn2.close()


def test_upsert_institution(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase Bank", "chase.com")
    upsert_institution(conn, "chase-1", "Chase", "chase.com")  # update name

    row = conn.execute("SELECT name FROM institutions WHERE id = ?", ("chase-1",)).fetchone()
    assert row[0] == "Chase"
    conn.close()


def test_upsert_account(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution, upsert_account
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    row = conn.execute("SELECT name, type FROM accounts WHERE id = ?", ("acct-1",)).fetchone()
    assert row[0] == "Checking"
    assert row[1] == "checking"
    conn.close()


def test_upsert_transaction_dedup(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", pending=False, raw_json='{}')
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS #123", pending=False, raw_json='{}')

    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 1
    # Description updated on second upsert
    desc = conn.execute("SELECT description FROM transactions WHERE id = ?", ("txn-1",)).fetchone()[0]
    assert desc == "WHOLE FOODS #123"
    conn.close()


def test_snapshot_balance(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution, upsert_account, snapshot_balance
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    snapshot_balance(conn, "acct-1", "2026-03-01", 4230.50, 4200.00)
    snapshot_balance(conn, "acct-1", "2026-03-01", 4235.00, 4205.00)  # replace same day

    row = conn.execute("SELECT balance FROM balances WHERE account_id = ? AND date = ?",
                       ("acct-1", "2026-03-01")).fetchone()
    assert row[0] == 4235.00
    conn.close()
