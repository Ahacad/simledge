"""Budget management — TOML-based monthly category budgets."""

import calendar
import os
import tomllib
from datetime import date

from simledge.analysis import _account_filter
from simledge.log import setup_logging

log = setup_logging("simledge.budget")

DEFAULT_BUDGETS_TOML = """\
# SimpLedge monthly budgets
# Edit this file to set spending limits per category.
# Category names should match your rules (e.g. "Food:Dining", "Groceries").

# [[budgets]]
# category = "Groceries"
# monthly_limit = 400.00

# [[budgets]]
# category = "Food:Dining"
# monthly_limit = 500.00

# [[budgets]]
# category = "Entertainment:Streaming"
# monthly_limit = 50.00
"""


def init_budgets(path):
    """Write default budgets file. Does nothing if file already exists."""
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(DEFAULT_BUDGETS_TOML)
    log.info("initialized default budgets at %s", path)
    return True


def migrate_from_db(conn, path):
    """One-time migration: copy budgets from SQLite to TOML if TOML is empty."""
    if os.path.exists(path) and load_budgets(path):
        return 0
    try:
        rows = conn.execute(
            "SELECT category, monthly_limit FROM budgets ORDER BY category"
        ).fetchall()
    except Exception:
        return 0
    if not rows:
        return 0
    budgets = [{"category": r[0], "monthly_limit": r[1]} for r in rows]
    save_budgets(path, budgets)
    log.info("migrated %d budgets from SQLite to %s", len(budgets), path)
    return len(budgets)


def load_budgets(path):
    """Load budgets from a TOML file. Returns list of dicts."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return []
    raw = data.get("budgets", [])
    budgets = []
    for b in raw:
        if "category" not in b or "monthly_limit" not in b:
            continue
        budgets.append(
            {"category": b["category"], "monthly_limit": float(b["monthly_limit"])}
        )
    return budgets


def save_budgets(path, budgets):
    """Write budgets list to a TOML file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# SimpLedge monthly budgets",
        "# Edit this file to set spending limits per category.",
        '# Category names should match your rules (e.g. "Food:Dining", "Groceries").',
        "",
    ]
    for b in budgets:
        lines.append("[[budgets]]")
        lines.append(f'category = "{b["category"]}"')
        lines.append(f"monthly_limit = {b['monthly_limit']:.2f}")
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def get_budgets(path):
    """Get all budgets from TOML file."""
    return load_budgets(path)


def set_budget(path, category, monthly_limit):
    """Add or update a budget entry."""
    budgets = load_budgets(path)
    for b in budgets:
        if b["category"].lower() == category.lower():
            b["monthly_limit"] = monthly_limit
            save_budgets(path, budgets)
            return
    budgets.append({"category": category, "monthly_limit": monthly_limit})
    save_budgets(path, budgets)


def delete_budget(path, category):
    """Remove a budget entry by category name."""
    budgets = load_budgets(path)
    budgets = [b for b in budgets if b["category"].lower() != category.lower()]
    save_budgets(path, budgets)


def budget_vs_actual(conn, month, path=None, account_ids=None):
    """Compare budgets against actual spending for a month."""
    if path is None:
        from simledge.config import BUDGETS_PATH

        path = BUDGETS_PATH
    budgets = load_budgets(path)
    if not budgets:
        return []

    filt, filt_params = _account_filter(account_ids)
    result = []
    for b in budgets:
        row = conn.execute(
            "SELECT COALESCE(SUM(ABS(amount)), 0)"
            " FROM transactions"
            " WHERE LOWER(category) = LOWER(?)"
            " AND strftime('%Y-%m', posted) = ?"
            " AND amount < 0" + filt,
            [b["category"], month, *filt_params],
        ).fetchone()
        actual = row[0]
        budget = b["monthly_limit"]
        remaining = budget - actual
        pct = (actual / budget * 100) if budget > 0 else 0
        result.append(
            {
                "category": b["category"],
                "budget": budget,
                "actual": actual,
                "remaining": remaining,
                "pct_used": round(pct, 1),
            }
        )
    result.sort(key=lambda r: r["actual"], reverse=True)
    return result


def total_budget_summary(conn, month, path=None, account_ids=None):
    """Compute totals across all budgets for a month."""
    items = budget_vs_actual(conn, month, path=path, account_ids=account_ids)

    total_budgeted = sum(i["budget"] for i in items)
    total_actual = sum(i["actual"] for i in items)
    total_remaining = total_budgeted - total_actual

    filt, filt_params = _account_filter(account_ids)
    row = conn.execute(
        "SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions"
        " WHERE amount < 0 AND strftime('%Y-%m', posted) = ?" + filt,
        [month, *filt_params],
    ).fetchone()
    all_spending = row[0]
    unbudgeted_spending = all_spending - total_actual

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
