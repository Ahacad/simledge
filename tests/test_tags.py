# tests/test_tags.py
from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction


def _seed_db(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Test Bank", "test.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -50.00, "TEST_STORE", category="shopping")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -30.00, "TEST_GAS", category="gas")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-03", -80.00, "TEST_FOOD", category="groceries")
    return conn


def test_create_tag(tmp_path):
    from simledge.tags import create_tag, list_tags
    conn = _seed_db(tmp_path)
    tag_id = create_tag(conn, "vacation")
    assert tag_id is not None
    tags = list_tags(conn)
    assert any(t["name"] == "vacation" for t in tags)
    conn.close()


def test_get_or_create_tag(tmp_path):
    from simledge.tags import get_or_create_tag
    conn = _seed_db(tmp_path)
    id1 = get_or_create_tag(conn, "trip")
    id2 = get_or_create_tag(conn, "trip")
    assert id1 == id2
    conn.close()


def test_tag_transaction(tmp_path):
    from simledge.tags import tag_transaction, get_transaction_tags
    conn = _seed_db(tmp_path)
    tag_transaction(conn, "t1", "vancouver")
    tags = get_transaction_tags(conn, "t1")
    assert "vancouver" in tags
    # Idempotent re-tag
    tag_transaction(conn, "t1", "vancouver")
    tags = get_transaction_tags(conn, "t1")
    assert tags.count("vancouver") == 1
    conn.close()


def test_untag_transaction(tmp_path):
    from simledge.tags import tag_transaction, untag_transaction, get_transaction_tags
    conn = _seed_db(tmp_path)
    tag_transaction(conn, "t1", "ski-trip")
    untag_transaction(conn, "t1", "ski-trip")
    tags = get_transaction_tags(conn, "t1")
    assert "ski-trip" not in tags
    conn.close()


def test_get_transaction_tags(tmp_path):
    from simledge.tags import tag_transaction, get_transaction_tags
    conn = _seed_db(tmp_path)
    tag_transaction(conn, "t1", "travel")
    tag_transaction(conn, "t1", "food")
    tag_transaction(conn, "t1", "weekend")
    tags = get_transaction_tags(conn, "t1")
    assert len(tags) == 3
    assert set(tags) == {"travel", "food", "weekend"}
    conn.close()


def test_set_transaction_tags(tmp_path):
    from simledge.tags import tag_transaction, set_transaction_tags, get_transaction_tags
    conn = _seed_db(tmp_path)
    tag_transaction(conn, "t1", "old-tag")
    set_transaction_tags(conn, "t1", ["new-a", "new-b"])
    tags = get_transaction_tags(conn, "t1")
    assert set(tags) == {"new-a", "new-b"}
    assert "old-tag" not in tags
    conn.close()


def test_spending_by_tag(tmp_path):
    from simledge.tags import tag_transaction
    from simledge.analysis import spending_by_tag
    conn = _seed_db(tmp_path)
    tag_transaction(conn, "t1", "vancouver")
    tag_transaction(conn, "t2", "vancouver")
    result = spending_by_tag(conn, "2026-03")
    assert len(result) == 1
    assert result[0]["tag"] == "vancouver"
    assert result[0]["total"] == -80.00  # -50 + -30
    conn.close()


def test_spending_by_tag_multi(tmp_path):
    from simledge.tags import tag_transaction
    from simledge.analysis import spending_by_tag
    conn = _seed_db(tmp_path)
    # t1 tagged with both "trip" and "weekend"
    tag_transaction(conn, "t1", "trip")
    tag_transaction(conn, "t1", "weekend")
    # t2 tagged with "trip" only
    tag_transaction(conn, "t2", "trip")
    result = spending_by_tag(conn, "2026-03")
    by_tag = {r["tag"]: r["total"] for r in result}
    assert by_tag["trip"] == -80.00  # t1(-50) + t2(-30)
    assert by_tag["weekend"] == -50.00  # t1 only
    conn.close()
