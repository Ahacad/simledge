"""Tests for TOML-based category rule engine."""


def test_init_rules_creates_file(tmp_path):
    from simledge.categorize import init_rules

    path = tmp_path / "rules.toml"
    init_rules(str(path))
    assert path.exists()
    content = path.read_text()
    assert "[[rules]]" in content
    assert '"Groceries"' in content


def test_init_rules_does_not_overwrite(tmp_path):
    from simledge.categorize import init_rules

    path = tmp_path / "rules.toml"
    path.write_text("# my custom rules\n")
    init_rules(str(path))
    assert path.read_text() == "# my custom rules\n"


def test_load_rules_reads_toml(tmp_path):
    from simledge.categorize import load_rules

    path = tmp_path / "rules.toml"
    path.write_text(
        '[[rules]]\npattern = "COSTCO"\ncategory = "Food:Groceries"\npriority = 5\n\n'
        '[[rules]]\npattern = "NETFLIX"\ncategory = "Entertainment:Streaming"\n'
    )
    rules = load_rules(str(path))
    assert len(rules) == 2
    assert rules[0]["pattern"] == "COSTCO"
    assert rules[0]["category"] == "Food:Groceries"
    assert rules[0]["priority"] == 5
    assert rules[1]["priority"] == 0  # default


def test_load_rules_returns_empty_if_missing(tmp_path):
    from simledge.categorize import load_rules

    rules = load_rules(str(tmp_path / "nonexistent.toml"))
    assert rules == []


def test_save_rules_writes_toml(tmp_path):
    from simledge.categorize import load_rules, save_rules

    path = tmp_path / "rules.toml"
    rules = [
        {"pattern": "COSTCO", "category": "Food:Groceries", "priority": 5},
        {"pattern": "NETFLIX", "category": "Entertainment:Streaming", "priority": 0},
    ]
    save_rules(str(path), rules)

    loaded = load_rules(str(path))
    assert len(loaded) == 2
    assert loaded[0]["pattern"] == "COSTCO"
    assert loaded[0]["priority"] == 5
    assert loaded[1]["pattern"] == "NETFLIX"
    assert loaded[1]["priority"] == 0


def test_save_rules_preserves_order(tmp_path):
    from simledge.categorize import load_rules, save_rules

    path = tmp_path / "rules.toml"
    rules = [
        {"pattern": "AAA", "category": "Cat:A", "priority": 0},
        {"pattern": "ZZZ", "category": "Cat:Z", "priority": 10},
        {"pattern": "MMM", "category": "Cat:M", "priority": 5},
    ]
    save_rules(str(path), rules)
    loaded = load_rules(str(path))
    assert [r["pattern"] for r in loaded] == ["AAA", "ZZZ", "MMM"]


def test_apply_rules_categorizes_transactions(tmp_path):
    from simledge.categorize import apply_rules
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT #123")
    upsert_transaction(conn, "txn-2", "acct-1", "2026-03-01", -15.99, "NETFLIX.COM")

    rules = [
        {"pattern": "WHOLE FOODS", "category": "Food:Groceries", "priority": 0},
        {"pattern": "NETFLIX", "category": "Entertainment:Streaming", "priority": 0},
    ]
    count = apply_rules(rules, conn)

    assert count == 2
    row1 = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row1[0] == "Food:Groceries"
    row2 = conn.execute("SELECT category FROM transactions WHERE id='txn-2'").fetchone()
    assert row2[0] == "Entertainment:Streaming"
    conn.close()


def test_apply_rules_respects_priority(tmp_path):
    from simledge.categorize import apply_rules
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT")

    rules = [
        {"pattern": "WHOLE", "category": "generic", "priority": 0},
        {"pattern": "WHOLE FOODS", "category": "Food:Groceries", "priority": 10},
    ]
    apply_rules(rules, conn)

    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] == "Food:Groceries"
    conn.close()


def test_apply_rules_skips_already_categorized(tmp_path):
    from simledge.categorize import apply_rules
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(
        conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", category="food"
    )

    rules = [{"pattern": "WHOLE FOODS", "category": "Food:Groceries", "priority": 0}]
    count = apply_rules(rules, conn)

    assert count == 0
    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] == "food"
    conn.close()


def test_apply_rules_dry_run(tmp_path):
    from simledge.categorize import apply_rules
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT")

    rules = [{"pattern": "WHOLE FOODS", "category": "Food:Groceries", "priority": 0}]
    count = apply_rules(rules, conn, dry_run=True)

    assert count == 1
    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] is None
    conn.close()


def test_apply_rules_regex_fallback_to_substring(tmp_path):
    from simledge.categorize import apply_rules
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -10.00, "TEST MERCHANT")

    rules = [{"pattern": "[invalid", "category": "Test", "priority": 0}]
    count = apply_rules(rules, conn)

    assert count == 0
    conn.close()


def test_detect_cc_payments_tags_pair(tmp_path):
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-chk", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-cc", "org-1", "Credit Card", "USD", "credit")
    upsert_transaction(conn, "txn-out", "acct-chk", "2026-03-01", -500.00, "CHASE CARD AUTOPAY")
    upsert_transaction(conn, "txn-in", "acct-cc", "2026-03-01", 500.00, "PAYMENT THANK YOU")

    count = detect_cc_payments(conn)
    assert count == 2
    cat_out = conn.execute("SELECT category FROM transactions WHERE id='txn-out'").fetchone()[0]
    cat_in = conn.execute("SELECT category FROM transactions WHERE id='txn-in'").fetchone()[0]
    assert cat_out == "Transfer:Credit Card Payment"
    assert cat_in == "Transfer:Credit Card Payment"
    conn.close()


def test_detect_cc_payments_any_description(tmp_path):
    """Any same-day/same-amount pair with one CC account should match, regardless of description."""
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-chk", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-cc", "org-1", "Credit Card", "USD", "credit")
    upsert_transaction(conn, "txn-out", "acct-chk", "2026-03-01", -75.00, "CHASE EPAY")
    upsert_transaction(conn, "txn-in", "acct-cc", "2026-03-01", 75.00, "ELECTRONIC PMT")

    count = detect_cc_payments(conn)
    assert count == 2
    conn.close()


def test_detect_cc_payments_requires_cc_account(tmp_path):
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-chk1", "org-1", "Checking 1", "USD", "checking")
    upsert_account(conn, "acct-chk2", "org-1", "Checking 2", "USD", "checking")
    upsert_transaction(conn, "txn-out", "acct-chk1", "2026-03-01", -500.00, "ONLINE PAYMENT")
    upsert_transaction(conn, "txn-in", "acct-chk2", "2026-03-01", 500.00, "PAYMENT RECEIVED")

    count = detect_cc_payments(conn)
    assert count == 0
    conn.close()


def test_detect_cc_payments_skips_already_categorized(tmp_path):
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-chk", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-cc", "org-1", "Credit Card", "USD", "credit")
    upsert_transaction(
        conn, "txn-out", "acct-chk", "2026-03-01", -500.00, "AUTOPAY", category="Bills"
    )
    upsert_transaction(conn, "txn-in", "acct-cc", "2026-03-01", 500.00, "PAYMENT THANK YOU")

    count = detect_cc_payments(conn)
    assert count == 1
    cat_out = conn.execute("SELECT category FROM transactions WHERE id='txn-out'").fetchone()[0]
    assert cat_out == "Bills"
    cat_in = conn.execute("SELECT category FROM transactions WHERE id='txn-in'").fetchone()[0]
    assert cat_in == "Transfer:Credit Card Payment"
    conn.close()


def test_detect_cc_payments_null_type_with_payment_description(tmp_path):
    """When CC account has NULL type, fall back to description matching."""
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-chk", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-cfu", "org-1", "Chase Freedom Unlimited", "USD", None)

    upsert_transaction(
        conn,
        "txn-out",
        "acct-chk",
        "2026-03-01",
        -2000.00,
        "PAYMENT TO CHASE CARD ENDING IN 2348",
    )
    upsert_transaction(
        conn,
        "txn-in",
        "acct-cfu",
        "2026-03-01",
        2000.00,
        "PAYMENT-THANK YOU",
    )

    count = detect_cc_payments(conn)
    assert count == 2
    cat_out = conn.execute("SELECT category FROM transactions WHERE id='txn-out'").fetchone()[0]
    cat_in = conn.execute("SELECT category FROM transactions WHERE id='txn-in'").fetchone()[0]
    assert cat_out == "Transfer:Credit Card Payment"
    assert cat_in == "Transfer:Credit Card Payment"
    conn.close()


def test_detect_cc_payments_null_type_without_payment_description(tmp_path):
    """NULL-type account pair without payment description should NOT match."""
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-chk", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-unk", "org-1", "Some Account", "USD", None)

    upsert_transaction(conn, "txn-out", "acct-chk", "2026-03-01", -500.00, "TRANSFER OUT")
    upsert_transaction(conn, "txn-in", "acct-unk", "2026-03-01", 500.00, "DEPOSIT")

    count = detect_cc_payments(conn)
    assert count == 0
    conn.close()


def test_detect_cc_payments_no_match_without_cc_account(tmp_path):
    """Same-day/same-amount pair between two non-CC accounts should NOT match."""
    from simledge.categorize import detect_cc_payments
    from simledge.db import init_db, upsert_account, upsert_institution, upsert_transaction

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-sav", "org-1", "Savings", "USD", "savings")
    upsert_account(conn, "acct-chk", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-out", "acct-chk", "2026-03-01", -1200.00, "TRANSFER TO SAVINGS")
    upsert_transaction(conn, "txn-in", "acct-sav", "2026-03-01", 1200.00, "TRANSFER FROM CHECKING")

    count = detect_cc_payments(conn)
    assert count == 0
    conn.close()
