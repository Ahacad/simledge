# tests/test_db.py


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
    from simledge.db import init_db, upsert_account, upsert_institution

    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    row = conn.execute("SELECT name, type FROM accounts WHERE id = ?", ("acct-1",)).fetchone()
    assert row[0] == "Checking"
    assert row[1] == "checking"
    conn.close()


def test_upsert_transaction_dedup(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    upsert_transaction(
        conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", pending=False, raw_json="{}"
    )
    upsert_transaction(
        conn,
        "txn-1",
        "acct-1",
        "2026-03-01",
        -47.32,
        "WHOLE FOODS #123",
        pending=False,
        raw_json="{}",
    )

    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 1
    # Description updated on second upsert
    desc = conn.execute("SELECT description FROM transactions WHERE id = ?", ("txn-1",)).fetchone()[
        0
    ]
    assert desc == "WHOLE FOODS #123"
    conn.close()


def test_snapshot_balance(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, snapshot_balance, upsert_account, upsert_institution

    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    snapshot_balance(conn, "acct-1", "2026-03-01", 4230.50, 4200.00)
    snapshot_balance(conn, "acct-1", "2026-03-01", 4235.00, 4205.00)  # replace same day

    row = conn.execute(
        "SELECT balance FROM balances WHERE account_id = ? AND date = ?", ("acct-1", "2026-03-01")
    ).fetchone()
    assert row[0] == 4235.00
    conn.close()


def _setup_txn(tmp_path):
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    upsert_institution(conn, "bank-1", "Test Bank", "test.com")
    upsert_account(conn, "acct-1", "bank-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -100.00, "TEST_MERCHANT")
    return conn


def test_update_transaction_field_category(tmp_path):
    from simledge.db import update_transaction_field

    conn = _setup_txn(tmp_path)
    update_transaction_field(conn, "txn-1", "category", "groceries")
    row = conn.execute("SELECT category FROM transactions WHERE id = ?", ("txn-1",)).fetchone()
    assert row[0] == "groceries"
    conn.close()


def test_update_transaction_field_notes(tmp_path):
    from simledge.db import update_transaction_field

    conn = _setup_txn(tmp_path)
    update_transaction_field(conn, "txn-1", "notes", "weekly shopping")
    row = conn.execute("SELECT notes FROM transactions WHERE id = ?", ("txn-1",)).fetchone()
    assert row[0] == "weekly shopping"
    conn.close()


def test_update_transaction_field_rejects_invalid(tmp_path):
    import pytest

    from simledge.db import update_transaction_field

    conn = _setup_txn(tmp_path)
    with pytest.raises(ValueError, match="not editable"):
        update_transaction_field(conn, "txn-1", "amount", "999")
    conn.close()


def test_get_transaction(tmp_path):
    from simledge.db import get_transaction

    conn = _setup_txn(tmp_path)
    txn = get_transaction(conn, "txn-1")
    assert txn["id"] == "txn-1"
    assert txn["description"] == "TEST_MERCHANT"
    assert txn["amount"] == -100.00
    assert txn["account"] == "Checking"
    assert txn["institution"] == "Test Bank"
    conn.close()


def test_get_transaction_missing(tmp_path):
    from simledge.db import get_transaction, init_db

    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    assert get_transaction(conn, "nonexistent") is None
    conn.close()


def test_display_name_migration(tmp_path):
    from simledge.db import init_db

    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(accounts)").fetchall()}
    assert "display_name" in cols
    conn.close()


def test_update_account_display_name(tmp_path):
    from simledge.db import init_db, update_account_display_name, upsert_account, upsert_institution

    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    upsert_institution(conn, "bank-1", "Test Bank", "test.com")
    upsert_account(conn, "acct-1", "bank-1", "Very Long Account Name", "USD", "checking")

    update_account_display_name(conn, "acct-1", "Checking")
    row = conn.execute("SELECT display_name FROM accounts WHERE id = ?", ("acct-1",)).fetchone()
    assert row[0] == "Checking"

    # Clear display name
    update_account_display_name(conn, "acct-1", "")
    row = conn.execute("SELECT display_name FROM accounts WHERE id = ?", ("acct-1",)).fetchone()
    assert row[0] is None
    conn.close()
