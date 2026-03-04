"""Savings goals — CRUD and progress tracking."""

from datetime import datetime

from simledge.log import setup_logging

log = setup_logging("simledge.goals")


def create_goal(conn, name, target_amount, target_date=None, account_id=None):
    starting_balance = 0
    if account_id:
        row = conn.execute(
            "SELECT balance FROM balances WHERE account_id = ? ORDER BY date DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if row:
            starting_balance = row[0]
    conn.execute(
        "INSERT INTO goals (name, target_amount, target_date, account_id,"
        " starting_balance) VALUES (?, ?, ?, ?, ?)",
        (name, target_amount, target_date, account_id, starting_balance),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_goals(conn):
    rows = conn.execute(
        "SELECT id, name, target_amount, target_date, account_id,"
        " starting_balance, created_at FROM goals ORDER BY id"
    ).fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "target_amount": r[2],
            "target_date": r[3],
            "account_id": r[4],
            "starting_balance": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]


def update_goal(conn, goal_id, name=None, target_amount=None, target_date=None):
    updates, params = [], []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if target_amount is not None:
        updates.append("target_amount = ?")
        params.append(target_amount)
    if target_date is not None:
        updates.append("target_date = ?")
        params.append(target_date)
    if not updates:
        return
    params.append(goal_id)
    conn.execute(f"UPDATE goals SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()


def delete_goal(conn, goal_id):
    conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    conn.commit()


def goal_progress(conn, goal_id):
    row = conn.execute(
        "SELECT id, name, target_amount, target_date, account_id,"
        " starting_balance FROM goals WHERE id = ?",
        (goal_id,),
    ).fetchone()
    if not row:
        return None

    goal_id, name, target, target_date, account_id, starting_bal = row

    current_amount = 0
    linked = False
    if account_id:
        bal_row = conn.execute(
            "SELECT balance FROM balances WHERE account_id = ? ORDER BY date DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if bal_row:
            current_amount = bal_row[0] - starting_bal
            linked = True

    remaining = max(target - current_amount, 0)
    pct = (current_amount / target * 100) if target > 0 else 0
    pct = min(pct, 100)

    monthly_needed = None
    on_track = None
    if target_date:
        try:
            td = datetime.strptime(target_date, "%Y-%m-%d")
            now = datetime.now()
            if td > now:
                months_left = (td.year - now.year) * 12 + (td.month - now.month)
                if months_left > 0:
                    monthly_needed = remaining / months_left
                    on_track = pct >= 0
        except ValueError:
            pass

    return {
        "id": goal_id,
        "name": name,
        "target_amount": target,
        "current_amount": current_amount,
        "remaining": remaining,
        "pct_complete": round(pct, 1),
        "target_date": target_date,
        "monthly_needed": round(monthly_needed, 2) if monthly_needed is not None else None,
        "on_track": on_track,
        "linked": linked,
    }


def all_goals_progress(conn):
    goals = get_goals(conn)
    return [goal_progress(conn, g["id"]) for g in goals]
