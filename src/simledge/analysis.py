"""Structured analysis queries against the local database."""

from datetime import datetime, timedelta


def spending_by_category(conn, month):
    """Return spending grouped by category for a YYYY-MM month."""
    rows = conn.execute(
        "SELECT COALESCE(category, 'uncategorized') as cat, SUM(amount) as total"
        " FROM transactions"
        " WHERE strftime('%Y-%m', posted) = ? AND amount < 0"
        " GROUP BY cat ORDER BY total ASC",
        (month,),
    ).fetchall()
    return [{"category": r[0], "total": r[1]} for r in rows]


def monthly_summary(conn, month):
    """Return total spending, income, and net for a month."""
    row = conn.execute(
        "SELECT"
        " COALESCE(SUM(CASE WHEN amount < 0 THEN amount END), 0),"
        " COALESCE(SUM(CASE WHEN amount > 0 THEN amount END), 0)"
        " FROM transactions WHERE strftime('%Y-%m', posted) = ?",
        (month,),
    ).fetchone()
    spending, income = row[0], row[1]
    return {"total_spending": spending, "total_income": income, "net": income + spending}


def net_worth_on_date(conn, date):
    """Sum all account balances for a given date."""
    row = conn.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM balances WHERE date = ?",
        (date,),
    ).fetchone()
    return row[0]


def net_worth_history(conn, months=6):
    """Return net worth per month for the last N months."""
    rows = conn.execute(
        "SELECT date, SUM(balance) as total FROM balances"
        " GROUP BY date ORDER BY date DESC LIMIT ?",
        (months * 31,),  # rough upper bound on daily snapshots
    ).fetchall()
    # Deduplicate to one per month (latest date in each month)
    by_month = {}
    for date, total in rows:
        month = date[:7]
        if month not in by_month:
            by_month[month] = total
    result = [{"month": m, "net_worth": v} for m, v in sorted(by_month.items())]
    return result


def spending_trend(conn, months=6):
    """Return total spending per month for the last N months."""
    today = datetime.now()
    start = today - timedelta(days=months * 31)
    start_str = start.strftime("%Y-%m-%d")

    rows = conn.execute(
        "SELECT strftime('%Y-%m', posted) as month, SUM(amount) as total"
        " FROM transactions WHERE amount < 0 AND posted >= ?"
        " GROUP BY month ORDER BY month",
        (start_str,),
    ).fetchall()
    return [{"month": r[0], "total": r[1]} for r in rows]


def recent_transactions(conn, limit=20):
    """Return the most recent transactions."""
    rows = conn.execute(
        "SELECT t.id, t.posted, t.amount, t.description, t.category, t.pending,"
        " a.name as account_name"
        " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        " ORDER BY t.posted DESC, t.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {"id": r[0], "posted": r[1], "amount": r[2], "description": r[3],
         "category": r[4], "pending": bool(r[5]), "account": r[6]}
        for r in rows
    ]


def account_summary(conn):
    """Return all accounts with latest balance, grouped by institution."""
    rows = conn.execute(
        "SELECT a.id, a.name, a.type, a.currency, i.name as institution,"
        " b.balance, b.available_balance, b.date"
        " FROM accounts a"
        " LEFT JOIN institutions i ON a.institution_id = i.id"
        " LEFT JOIN balances b ON a.id = b.account_id"
        "  AND b.date = (SELECT MAX(date) FROM balances WHERE account_id = a.id)"
        " ORDER BY i.name, a.name",
    ).fetchall()
    return [
        {"id": r[0], "name": r[1], "type": r[2], "currency": r[3],
         "institution": r[4], "balance": r[5], "available_balance": r[6],
         "balance_date": r[7]}
        for r in rows
    ]
