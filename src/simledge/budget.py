"""Budget CRUD and budget-vs-actual comparison queries."""

import calendar
from datetime import date

from simledge.analysis import _account_filter


def set_budget(conn, category, monthly_limit):
    conn.execute(
        "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)"
        " ON CONFLICT(category) DO UPDATE SET monthly_limit=excluded.monthly_limit",
        (category, monthly_limit),
    )
    conn.commit()


def get_budgets(conn):
    rows = conn.execute(
        "SELECT id, category, monthly_limit FROM budgets ORDER BY category"
    ).fetchall()
    return [{"id": r[0], "category": r[1], "monthly_limit": r[2]} for r in rows]


def delete_budget(conn, budget_id):
    conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()


def budget_vs_actual(conn, month, account_ids=None):
    filt, filt_params = _account_filter(account_ids)
    rows = conn.execute(
        "SELECT b.category, b.monthly_limit,"
        " COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) END), 0) as actual"
        " FROM budgets b"
        " LEFT JOIN transactions t"
        "   ON LOWER(t.category) = LOWER(b.category)"
        "   AND strftime('%Y-%m', t.posted) = ?"
        + filt.replace("account_id", "t.account_id")
        + " GROUP BY b.category, b.monthly_limit"
        " ORDER BY actual DESC",
        [month, *filt_params],
    ).fetchall()
    result = []
    for r in rows:
        budget = r[1]
        actual = r[2]
        remaining = budget - actual
        pct = (actual / budget * 100) if budget > 0 else 0
        result.append(
            {
                "category": r[0],
                "budget": budget,
                "actual": actual,
                "remaining": remaining,
                "pct_used": round(pct, 1),
            }
        )
    return result


def total_budget_summary(conn, month, account_ids=None):
    items = budget_vs_actual(conn, month, account_ids=account_ids)

    total_budgeted = sum(i["budget"] for i in items)
    total_actual = sum(i["actual"] for i in items)
    total_remaining = total_budgeted - total_actual

    # Unbudgeted spending: total spending minus spending in budgeted categories
    filt, filt_params = _account_filter(account_ids)
    row = conn.execute(
        "SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions"
        " WHERE amount < 0 AND strftime('%Y-%m', posted) = ?" + filt,
        [month, *filt_params],
    ).fetchone()
    all_spending = row[0]
    unbudgeted_spending = all_spending - total_actual

    # Days remaining
    today = date.today()
    try:
        year, mon = int(month[:4]), int(month[5:])
        _, last_day = calendar.monthrange(year, mon)
        month_end = date(year, mon, last_day)
        if today > month_end:
            days_remaining = 0
        elif today.strftime("%Y-%m") == month:
            days_remaining = (month_end - today).days + 1
        else:
            days_remaining = last_day
    except (ValueError, IndexError):
        days_remaining = 0

    daily_pace = (total_remaining / days_remaining) if days_remaining > 0 else 0

    return {
        "total_budgeted": total_budgeted,
        "total_actual": total_actual,
        "total_remaining": total_remaining,
        "unbudgeted_spending": unbudgeted_spending,
        "days_remaining": days_remaining,
        "daily_pace": round(daily_pace, 2),
    }
