"""Structured analysis queries against the local database."""

from datetime import datetime, timedelta


def _account_filter(account_ids, table_prefix="", column=None):
    """Build WHERE clause fragment and params for account_id filtering."""
    if account_ids is None:
        return "", []
    ids = list(account_ids)
    placeholders = ",".join("?" for _ in ids)
    col = column or (f"{table_prefix}account_id" if table_prefix else "account_id")
    return f" AND {col} IN ({placeholders})", ids


def spending_by_category(conn, month, account_ids=None):
    """Return spending grouped by category for a YYYY-MM month."""
    filt, filt_params = _account_filter(account_ids)
    rows = conn.execute(
        "SELECT COALESCE(category, 'uncategorized') as cat, SUM(amount) as total"
        " FROM transactions"
        " WHERE strftime('%Y-%m', posted) = ? AND amount < 0"
        + filt
        + " GROUP BY cat ORDER BY total ASC",
        [month] + filt_params,
    ).fetchall()
    return [{"category": r[0], "total": r[1]} for r in rows]


def monthly_summary(conn, month, account_ids=None):
    """Return total spending, income, and net for a month."""
    filt, filt_params = _account_filter(account_ids)
    row = conn.execute(
        "SELECT"
        " COALESCE(SUM(CASE WHEN amount < 0 THEN amount END), 0),"
        " COALESCE(SUM(CASE WHEN amount > 0 THEN amount END), 0)"
        " FROM transactions WHERE strftime('%Y-%m', posted) = ?"
        + filt,
        [month] + filt_params,
    ).fetchone()
    spending, income = row[0], row[1]
    return {"total_spending": spending, "total_income": income, "net": income + spending}


def net_worth_on_date(conn, date, account_ids=None):
    """Sum all account balances for a given date."""
    filt, filt_params = _account_filter(account_ids)
    row = conn.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM balances WHERE date = ?"
        + filt,
        [date] + filt_params,
    ).fetchone()
    return row[0]


def net_worth_history(conn, months=6, account_ids=None):
    """Return net worth per month for the last N months."""
    filt, filt_params = _account_filter(account_ids)
    rows = conn.execute(
        "SELECT date, SUM(balance) as total FROM balances"
        " WHERE 1=1"
        + filt
        + " GROUP BY date ORDER BY date DESC LIMIT ?",
        filt_params + [months * 31],
    ).fetchall()
    # Deduplicate to one per month (latest date in each month)
    by_month = {}
    for date, total in rows:
        month = date[:7]
        if month not in by_month:
            by_month[month] = total
    result = [{"month": m, "net_worth": v} for m, v in sorted(by_month.items())]
    return result


def spending_trend(conn, months=6, account_ids=None):
    """Return total spending per month for the last N months."""
    today = datetime.now()
    start = today - timedelta(days=months * 31)
    start_str = start.strftime("%Y-%m-%d")

    filt, filt_params = _account_filter(account_ids)
    rows = conn.execute(
        "SELECT strftime('%Y-%m', posted) as month, SUM(amount) as total"
        " FROM transactions WHERE amount < 0 AND posted >= ?"
        + filt
        + " GROUP BY month ORDER BY month",
        [start_str] + filt_params,
    ).fetchall()
    return [{"month": r[0], "total": r[1]} for r in rows]


def income_by_category(conn, month, account_ids=None):
    """Return income grouped by category for a YYYY-MM month."""
    filt, filt_params = _account_filter(account_ids)
    rows = conn.execute(
        "SELECT COALESCE(category, 'uncategorized') as cat, SUM(amount) as total"
        " FROM transactions"
        " WHERE strftime('%Y-%m', posted) = ? AND amount > 0"
        + filt
        + " GROUP BY cat ORDER BY total DESC",
        [month] + filt_params,
    ).fetchall()
    return [{"category": r[0], "total": r[1]} for r in rows]


def income_trend(conn, months=6, account_ids=None):
    """Return total income per month for the last N months."""
    today = datetime.now()
    start = today - timedelta(days=months * 31)
    start_str = start.strftime("%Y-%m-%d")

    filt, filt_params = _account_filter(account_ids)
    rows = conn.execute(
        "SELECT strftime('%Y-%m', posted) as month, SUM(amount) as total"
        " FROM transactions WHERE amount > 0 AND posted >= ?"
        + filt
        + " GROUP BY month ORDER BY month",
        [start_str] + filt_params,
    ).fetchall()
    return [{"month": r[0], "total": r[1]} for r in rows]


def spending_by_category_grouped(conn, month, account_ids=None):
    """Return spending grouped by parent category with children breakdown."""
    flat = spending_by_category(conn, month, account_ids=account_ids)
    parents = {}
    order = []
    for entry in flat:
        cat = entry["category"]
        if ":" in cat:
            parent, _ = cat.split(":", 1)
        else:
            parent = cat
        if parent not in parents:
            parents[parent] = {"category": parent, "total": 0, "children": []}
            order.append(parent)
        parents[parent]["total"] += entry["total"]
        if ":" in cat:
            parents[parent]["children"].append(entry)
    # Sort children within each parent by total ascending (most spending first)
    for p in parents.values():
        p["children"].sort(key=lambda c: c["total"])
    return [parents[k] for k in order]


def spending_by_tag(conn, month, account_ids=None):
    """Return spending grouped by tag for a YYYY-MM month.

    A transaction with multiple tags appears in each tag's total.
    """
    filt, filt_params = _account_filter(account_ids, table_prefix="t.")
    rows = conn.execute(
        "SELECT tg.name, SUM(t.amount) as total"
        " FROM transactions t"
        " JOIN transaction_tags tt ON t.id = tt.transaction_id"
        " JOIN tags tg ON tt.tag_id = tg.id"
        " WHERE strftime('%Y-%m', t.posted) = ? AND t.amount < 0"
        + filt
        + " GROUP BY tg.name ORDER BY total ASC",
        [month] + filt_params,
    ).fetchall()
    return [{"tag": r[0], "total": r[1]} for r in rows]


def recent_transactions(conn, limit=20, account_ids=None):
    """Return the most recent transactions."""
    filt, filt_params = _account_filter(account_ids, table_prefix="t.")
    rows = conn.execute(
        "SELECT t.id, t.posted, t.amount, t.description, t.category, t.pending,"
        " a.name as account_name"
        " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        " WHERE 1=1"
        + filt
        + " ORDER BY t.posted DESC, t.id DESC LIMIT ?",
        filt_params + [limit],
    ).fetchall()
    return [
        {"id": r[0], "posted": r[1], "amount": r[2], "description": r[3],
         "category": r[4], "pending": bool(r[5]), "account": r[6]}
        for r in rows
    ]


def account_summary(conn, account_ids=None):
    """Return all accounts with latest balance, grouped by institution."""
    filt, filt_params = _account_filter(account_ids, column="a.id")
    rows = conn.execute(
        "SELECT a.id, a.name, a.type, a.currency, i.name as institution,"
        " b.balance, b.available_balance, b.date"
        " FROM accounts a"
        " LEFT JOIN institutions i ON a.institution_id = i.id"
        " LEFT JOIN balances b ON a.id = b.account_id"
        "  AND b.date = (SELECT MAX(date) FROM balances WHERE account_id = a.id)"
        " WHERE 1=1"
        + filt
        + " ORDER BY i.name, a.name",
        filt_params,
    ).fetchall()
    return [
        {"id": r[0], "name": r[1], "type": r[2], "currency": r[3],
         "institution": r[4], "balance": r[5], "available_balance": r[6],
         "balance_date": r[7]}
        for r in rows
    ]
