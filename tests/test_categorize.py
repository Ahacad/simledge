# tests/test_categorize.py

def test_apply_rules_matches_keyword(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    from simledge.categorize import add_rule, apply_rules

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT #123")
    upsert_transaction(conn, "txn-2", "acct-1", "2026-03-01", -23.99, "AMAZON.COM")

    add_rule(conn, "WHOLE FOODS", "groceries")
    add_rule(conn, "AMAZON", "shopping")
    count = apply_rules(conn)

    assert count == 2
    row1 = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row1[0] == "groceries"
    row2 = conn.execute("SELECT category FROM transactions WHERE id='txn-2'").fetchone()
    assert row2[0] == "shopping"
    conn.close()


def test_apply_rules_respects_priority(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    from simledge.categorize import add_rule, apply_rules

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT")

    add_rule(conn, "WHOLE", "generic", priority=0)
    add_rule(conn, "WHOLE FOODS", "groceries", priority=10)
    apply_rules(conn)

    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] == "groceries"
    conn.close()


def test_apply_rules_skips_already_categorized(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    from simledge.categorize import add_rule, apply_rules

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS",
                       category="food")

    add_rule(conn, "WHOLE FOODS", "groceries")
    count = apply_rules(conn)

    assert count == 0
    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] == "food"  # unchanged
    conn.close()


def test_list_rules(tmp_path):
    from simledge.db import init_db
    from simledge.categorize import add_rule, list_rules

    conn = init_db(str(tmp_path / "test.db"))
    add_rule(conn, "AMAZON", "shopping", priority=0)
    add_rule(conn, "WHOLE FOODS", "groceries", priority=10)

    rules = list_rules(conn)
    assert len(rules) == 2
    assert rules[0]["category"] == "groceries"  # higher priority first
    conn.close()
