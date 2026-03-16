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


def _build_full_data(conn, month, months=6, sections=None, account_ids=None, limit=500):
    """Gather comprehensive data for all requested sections."""
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

    return result


def export_json_full(conn, month, months=6, sections=None, account_ids=None, limit=500):
    """Comprehensive JSON export for AI consumption."""
    data = _build_full_data(conn, month, months, sections, account_ids, limit)
    return json.dumps(data, indent=2, default=str)


def export_csv_full(conn, month, months=6, sections=None, account_ids=None, limit=500):
    """Comprehensive CSV export — transactions with all metadata."""
    txns = _get_transactions(conn, month, account_ids=account_ids, limit=limit)
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["date", "description", "category", "amount", "account"]
    )
    writer.writeheader()
    writer.writerows(txns)
    return output.getvalue()


def _md_table(headers, rows):
    """Render a markdown table from headers and row tuples."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return lines


def export_markdown_full(conn, month, months=6, sections=None, account_ids=None, limit=500):
    """Comprehensive markdown export."""
    data = _build_full_data(conn, month, months, sections, account_ids, limit)
    active = data["meta"]["sections"]
    lines = [f"# SimpLedge Export — {month}", ""]

    if "summary" in active and "summary" in data:
        s = data["summary"]
        lines.append("## Summary")
        lines.append(f"- Total spending: ${abs(s['total_spending']):,.2f}")
        lines.append(f"- Total income: ${s['total_income']:,.2f}")
        lines.append(f"- Net: ${s['net']:+,.2f}")
        lines.append(f"- Daily average spending: ${s['daily_average_spending']:,.2f}")
        lines.append(f"- Uncategorized transactions: {s['uncategorized_count']}")
        lines.append("")

    if "spending" in active and "spending" in data:
        sp = data["spending"]
        if sp.get("by_category"):
            total_spend = sum(c["total"] for c in sp["by_category"])
            lines.append("## Spending by Category")
            rows = []
            for c in sp["by_category"]:
                pct = (c["total"] / total_spend * 100) if total_spend else 0
                rows.append((c["category"], f"${abs(c['total']):,.2f}", f"{pct:.1f}%"))
            lines.extend(_md_table(["Category", "Amount", "% of Total"], rows))
            lines.append("")

        if sp.get("by_tag"):
            lines.append("## Spending by Tag")
            rows = [(t["tag"], f"${abs(t['total']):,.2f}") for t in sp["by_tag"]]
            lines.extend(_md_table(["Tag", "Amount"], rows))
            lines.append("")

        if sp.get("top_merchants"):
            lines.append("## Top Merchants")
            rows = [
                (m["merchant"], f"${abs(m['total']):,.2f}", str(m["count"]))
                for m in sp["top_merchants"]
            ]
            lines.extend(_md_table(["Merchant", "Amount", "Transactions"], rows))
            lines.append("")

    if "income" in active and "income" in data:
        inc = data["income"].get("by_category", [])
        if inc:
            lines.append("## Income by Category")
            rows = [(i["category"], f"${i['total']:,.2f}") for i in inc]
            lines.extend(_md_table(["Category", "Amount"], rows))
            lines.append("")

    if "accounts" in active and "accounts" in data:
        accts = data["accounts"]
        if accts:
            lines.append("## Accounts")
            rows = []
            for a in accts:
                name = a.get("display_name") or a["name"]
                bal = f"${a['balance']:,.2f}" if a["balance"] is not None else "N/A"
                rows.append((a.get("institution", ""), name, a.get("type", ""), bal))
            lines.extend(_md_table(["Institution", "Account", "Type", "Balance"], rows))
            lines.append("")

    if "trends" in active and "trends" in data:
        tr = data["trends"]
        if tr.get("spending"):
            lines.append("## Spending Trend")
            rows = [(t["month"], f"${abs(t['total']):,.2f}") for t in tr["spending"]]
            lines.extend(_md_table(["Month", "Spending"], rows))
            lines.append("")

        if tr.get("income"):
            lines.append("## Income Trend")
            rows = [(t["month"], f"${t['total']:,.2f}") for t in tr["income"]]
            lines.extend(_md_table(["Month", "Income"], rows))
            lines.append("")

        if tr.get("net_worth"):
            lines.append("## Net Worth History")
            rows = [(t["month"], f"${t['net_worth']:,.2f}") for t in tr["net_worth"]]
            lines.extend(_md_table(["Month", "Net Worth"], rows))
            lines.append("")

    if "comparisons" in active and "comparisons" in data:
        cmp = data["comparisons"]
        if cmp.get("yoy"):
            y = cmp["yoy"]
            lines.append("## Year-over-Year Comparison")
            lines.append(f"- Current ({y['current_month']}): ${abs(y['current_spending']):,.2f}")
            lines.append(f"- Previous ({y['previous_month']}): ${abs(y['previous_spending']):,.2f}")
            if y.get("spending_change_pct") is not None:
                lines.append(f"- Change: {y['spending_change_pct']:+.1f}%")
            lines.append("")

        if cmp.get("ytd"):
            yt = cmp["ytd"]
            lines.append("## Year-to-Date")
            lines.append(
                f"- {yt['current_year']} spending ({yt['months_counted']}mo): "
                f"${abs(yt['current_spending']):,.2f}"
            )
            lines.append(f"- Previous year same period: ${abs(yt['previous_spending']):,.2f}")
            if yt.get("spending_change_pct") is not None:
                lines.append(f"- Change: {yt['spending_change_pct']:+.1f}%")
            lines.append("")

    if "budget" in active and "budget" in data:
        bd = data["budget"]
        if bd.get("items"):
            lines.append("## Budget vs Actual")
            rows = [
                (
                    b["category"],
                    f"${b['budget']:,.2f}",
                    f"${b['actual']:,.2f}",
                    f"${b['remaining']:,.2f}",
                    f"{b['pct_used']:.0f}%",
                )
                for b in bd["items"]
            ]
            lines.extend(_md_table(["Category", "Budget", "Actual", "Remaining", "Used"], rows))
            lines.append("")

    if "goals" in active and "goals" in data:
        goals = [g for g in data["goals"] if g]
        if goals:
            lines.append("## Goals")
            rows = [
                (
                    g["name"],
                    f"${g['target_amount']:,.2f}",
                    f"${g['current_amount']:,.2f}",
                    f"{g['pct_complete']:.0f}%",
                )
                for g in goals
            ]
            lines.extend(_md_table(["Goal", "Target", "Current", "Progress"], rows))
            lines.append("")

    if "watchlists" in active and "watchlists" in data:
        wl = [w for w in data["watchlists"] if w]
        if wl:
            lines.append("## Watchlists")
            rows = [
                (
                    w["name"],
                    f"${w['monthly_target']:,.2f}" if w.get("monthly_target") else "N/A",
                    f"${w['actual']:,.2f}",
                    "On track" if w.get("on_track") else "Over",
                )
                for w in wl
            ]
            lines.extend(_md_table(["Watchlist", "Target", "Actual", "Status"], rows))
            lines.append("")

    if "recurring" in active and "recurring" in data:
        rec = data["recurring"]
        if rec.get("detected"):
            lines.append("## Recurring Transactions")
            rows = [
                (
                    r["description"],
                    r["frequency"],
                    f"${abs(r['last_amount']):,.2f}",
                    r["next_expected"],
                )
                for r in rec["detected"]
            ]
            lines.extend(_md_table(["Description", "Frequency", "Amount", "Next Expected"], rows))
            lines.append("")

    if "cashflow" in active and "cashflow" in data:
        cf = data["cashflow"]
        if cf.get("summary"):
            s = cf["summary"]
            lines.append("## Cash Flow Projection")
            lines.append(f"- Current total: ${s['current_total']:,.2f}")
            lines.append(f"- 30-day: ${s['projected_30d']:,.2f}")
            lines.append(f"- 60-day: ${s['projected_60d']:,.2f}")
            lines.append(f"- 90-day: ${s['projected_90d']:,.2f}")
            if cf.get("negative_dates"):
                lines.append(f"- Warning: {len(cf['negative_dates'])} account(s) go negative")
            lines.append("")

    if "networth" in active and "networth" in data:
        nw = data["networth"]
        lines.append("## Net Worth")
        lines.append(f"- Current: ${nw['current']:,.2f}")
        lines.append("")

    if "transactions" in active and "transactions" in data:
        txn_data = data["transactions"]
        items = txn_data.get("items", [])
        if items:
            lines.append("## Transactions")
            if txn_data.get("truncated"):
                lines.append(
                    f"*Showing {txn_data['returned_count']} of "
                    f"{txn_data['total_count']} transactions*"
                )
                lines.append("")
            rows = [
                (t["date"], t["description"], t["category"], f"${t['amount']:+,.2f}", t["account"])
                for t in items
            ]
            lines.extend(_md_table(["Date", "Description", "Category", "Amount", "Account"], rows))
            lines.append("")

    return "\n".join(lines)
