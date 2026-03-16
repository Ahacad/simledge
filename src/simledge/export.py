"""Export data in markdown, CSV, or JSON for external analysis."""

import csv
import io
import json
from datetime import date, datetime

from simledge.analysis import (
    _account_filter,
    account_summary,
    daily_average_spending,
    income_by_category,
    income_trend,
    monthly_summary,
    net_worth_history,
    net_worth_on_date,
    spending_by_category,
    spending_by_category_grouped,
    spending_by_tag,
    spending_trend,
    top_merchants,
    uncategorized_count,
    yoy_comparison,
    ytd_comparison,
)


def _get_transactions(conn, month, account_ids=None, limit=None):
    filt, filt_params = _account_filter(account_ids, table_prefix="t.")
    limit_clause = f" LIMIT {int(limit)}" if limit else ""
    rows = conn.execute(
        "SELECT t.posted, t.description, COALESCE(t.category, 'uncategorized'),"
        " t.amount, a.name as account_name"
        " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        " WHERE strftime('%Y-%m', t.posted) = ?" + filt + " ORDER BY t.posted DESC" + limit_clause,
        (month, *filt_params),
    ).fetchall()
    return [
        {"date": r[0], "description": r[1], "category": r[2], "amount": r[3], "account": r[4]}
        for r in rows
    ]


def export_markdown(conn, month):
    summary = monthly_summary(conn, month)
    categories = spending_by_category(conn, month)
    transactions = _get_transactions(conn, month)

    lines = []
    lines.append(f"## SimpLedge Export — {month}")
    lines.append("")
    lines.append("### Summary")
    lines.append(f"- Total spending: ${abs(summary['total_spending']):,.2f}")
    lines.append(f"- Total income: ${summary['total_income']:,.2f}")
    lines.append(f"- Net: ${summary['net']:+,.2f}")
    lines.append("")

    if categories:
        total_spend = sum(c["total"] for c in categories)
        lines.append("### Spending by Category")
        lines.append("| Category | Amount | % of Total |")
        lines.append("| --- | --- | --- |")
        for c in categories:
            pct = (c["total"] / total_spend * 100) if total_spend else 0
            lines.append(f"| {c['category']} | ${abs(c['total']):,.2f} | {pct:.1f}% |")
        lines.append("")

    lines.append("### All Transactions")
    lines.append("| Date | Description | Category | Amount | Account |")
    lines.append("| --- | --- | --- | --- | --- |")
    for t in transactions:
        lines.append(
            f"| {t['date']} | {t['description']} | {t['category']}"
            f" | ${t['amount']:+,.2f} | {t['account']} |"
        )

    return "\n".join(lines)


def export_csv(conn, month):
    transactions = _get_transactions(conn, month)
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["date", "description", "category", "amount", "account"]
    )
    writer.writeheader()
    writer.writerows(transactions)
    return output.getvalue()


def export_json(conn, month):
    summary = monthly_summary(conn, month)
    categories = spending_by_category(conn, month)
    transactions = _get_transactions(conn, month)
    return json.dumps(
        {
            "month": month,
            "summary": summary,
            "categories": categories,
            "transactions": transactions,
        },
        indent=2,
    )


# --- Comprehensive structured export ---


def _get_version():
    try:
        from importlib.metadata import version

        return version("simledge")
    except Exception:
        return "unknown"


def _txn_count(conn, month, account_ids=None):
    filt, filt_params = _account_filter(account_ids)
    row = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', posted) = ?" + filt,
        [month, *filt_params],
    ).fetchone()
    return row[0]


def _build_summary(conn, month, months, account_ids, limit):
    s = monthly_summary(conn, month, account_ids=account_ids)
    s["daily_average_spending"] = daily_average_spending(conn, month, account_ids=account_ids)
    s["uncategorized_count"] = uncategorized_count(conn, month, account_ids=account_ids)
    return s


def _build_spending(conn, month, months, account_ids, limit):
    return {
        "by_category": spending_by_category(conn, month, account_ids=account_ids),
        "by_category_grouped": spending_by_category_grouped(conn, month, account_ids=account_ids),
        "by_tag": spending_by_tag(conn, month, account_ids=account_ids),
        "top_merchants": top_merchants(conn, month, account_ids=account_ids),
    }


def _build_income(conn, month, months, account_ids, limit):
    return {"by_category": income_by_category(conn, month, account_ids=account_ids)}


def _build_transactions(conn, month, months, account_ids, limit):
    total = _txn_count(conn, month, account_ids)
    items = _get_transactions(conn, month, account_ids=account_ids, limit=limit)
    return {
        "total_count": total,
        "returned_count": len(items),
        "limit": limit,
        "truncated": total > len(items),
        "items": items,
    }


def _build_accounts(conn, month, months, account_ids, limit):
    return account_summary(conn, account_ids=account_ids)


def _build_trends(conn, month, months, account_ids, limit):
    return {
        "spending": spending_trend(conn, months=months, account_ids=account_ids),
        "income": income_trend(conn, months=months, account_ids=account_ids),
        "net_worth": net_worth_history(conn, months=months, account_ids=account_ids),
    }


def _build_comparisons(conn, month, months, account_ids, limit):
    return {
        "yoy": yoy_comparison(conn, month, account_ids=account_ids),
        "ytd": ytd_comparison(conn, account_ids=account_ids),
    }


def _build_budget(conn, month, months, account_ids, limit):
    from simledge.budget import budget_vs_actual, total_budget_summary
    from simledge.config import BUDGETS_PATH

    items = budget_vs_actual(conn, month, path=BUDGETS_PATH, account_ids=account_ids)
    totals = total_budget_summary(conn, month, path=BUDGETS_PATH, account_ids=account_ids)
    return {"items": items, "totals": totals}


def _build_goals(conn, month, months, account_ids, limit):
    from simledge.goals import all_goals_progress

    return all_goals_progress(conn)


def _build_watchlists(conn, month, months, account_ids, limit):
    from simledge.watchlist import all_watchlist_spending

    return all_watchlist_spending(conn, month, account_ids=account_ids)


def _build_recurring(conn, month, months, account_ids, limit):
    from simledge.recurring import calendar_bills, detect_recurring

    return {
        "detected": detect_recurring(conn),
        "calendar": calendar_bills(conn, month),
    }


def _build_cashflow(conn, month, months, account_ids, limit):
    from simledge.cashflow import project_balances

    data = project_balances(conn, days=90, account_ids=account_ids)
    return {
        "summary": data["summary"],
        "negative_dates": data["negative_dates"],
    }


def _build_networth(conn, month, months, account_ids, limit):
    today = date.today().isoformat()
    return {
        "current": net_worth_on_date(conn, today, account_ids=account_ids),
        "history": net_worth_history(conn, months=months, account_ids=account_ids),
    }


SECTIONS = {
    "summary": _build_summary,
    "spending": _build_spending,
    "income": _build_income,
    "transactions": _build_transactions,
    "accounts": _build_accounts,
    "trends": _build_trends,
    "comparisons": _build_comparisons,
    "budget": _build_budget,
    "goals": _build_goals,
    "watchlists": _build_watchlists,
    "recurring": _build_recurring,
    "cashflow": _build_cashflow,
    "networth": _build_networth,
}

ALL_SECTIONS = list(SECTIONS.keys())


def export_json_full(conn, month, months=6, sections=None, account_ids=None, limit=500):
    """Comprehensive JSON export for AI consumption."""
    if sections is None:
        sections = ALL_SECTIONS

    result = {
        "meta": {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "month": month,
            "trend_months": months,
            "account_filter": list(account_ids) if account_ids else None,
            "sections": sections,
            "version": _get_version(),
        }
    }

    for section in sections:
        builder = SECTIONS.get(section)
        if not builder:
            continue
        try:
            result[section] = builder(conn, month, months, account_ids, limit)
        except Exception as e:
            result[section] = {"error": str(e)}

    return json.dumps(result, indent=2, default=str)
