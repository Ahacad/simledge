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
