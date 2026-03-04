# tests/test_goals.py


def _setup_db(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, snapshot_balance
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    upsert_institution(conn, "bank-1", "Test Bank", "test.com")
    upsert_account(conn, "acct-1", "bank-1", "Savings", "USD", "savings")
    snapshot_balance(conn, "acct-1", "2026-01-01", 1000.00)
    return conn


def test_create_goal_basic(tmp_path):
    from simledge.goals import create_goal, get_goals
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Emergency Fund", 10000.00)
    goals = get_goals(conn)
    assert len(goals) == 1
    assert goals[0]["name"] == "Emergency Fund"
    assert goals[0]["target_amount"] == 10000.00
    assert goals[0]["account_id"] is None
    assert goals[0]["starting_balance"] == 0
    conn.close()


def test_create_goal_with_account(tmp_path):
    from simledge.goals import create_goal, get_goals
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Vacation", 5000.00, account_id="acct-1")
    goals = get_goals(conn)
    assert len(goals) == 1
    assert goals[0]["account_id"] == "acct-1"
    assert goals[0]["starting_balance"] == 1000.00
    conn.close()


def test_goal_progress_linked(tmp_path):
    from simledge.db import snapshot_balance
    from simledge.goals import create_goal, goal_progress
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Vacation", 5000.00, account_id="acct-1")
    # Simulate balance growth
    snapshot_balance(conn, "acct-1", "2026-03-01", 3500.00)
    p = goal_progress(conn, goal_id)
    assert p["current_amount"] == 2500.00  # 3500 - 1000
    assert p["remaining"] == 2500.00
    assert p["pct_complete"] == 50.0
    assert p["linked"] is True
    conn.close()


def test_goal_progress_no_account(tmp_path):
    from simledge.goals import create_goal, goal_progress
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Emergency Fund", 10000.00)
    p = goal_progress(conn, goal_id)
    assert p["current_amount"] == 0
    assert p["pct_complete"] == 0.0
    assert p["linked"] is False
    conn.close()


def test_goal_monthly_needed(tmp_path):
    from simledge.goals import create_goal, goal_progress
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Car", 20000.00, target_date="2027-03-03")
    p = goal_progress(conn, goal_id)
    assert p["monthly_needed"] is not None
    assert p["monthly_needed"] > 0
    conn.close()


def test_goal_monthly_needed_past_date(tmp_path):
    from simledge.goals import create_goal, goal_progress
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Old Goal", 5000.00, target_date="2024-01-01")
    p = goal_progress(conn, goal_id)
    assert p["monthly_needed"] is None
    conn.close()


def test_delete_goal(tmp_path):
    from simledge.goals import create_goal, delete_goal, get_goals
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Test Goal", 1000.00)
    assert len(get_goals(conn)) == 1
    delete_goal(conn, goal_id)
    assert len(get_goals(conn)) == 0
    conn.close()


def test_update_goal(tmp_path):
    from simledge.goals import create_goal, update_goal, get_goals
    conn = _setup_db(tmp_path)
    goal_id = create_goal(conn, "Test Goal", 1000.00)
    update_goal(conn, goal_id, target_amount=2000.00)
    goals = get_goals(conn)
    assert goals[0]["target_amount"] == 2000.00
    conn.close()
