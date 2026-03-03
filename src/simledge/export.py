"""Export data in markdown, CSV, or JSON for external analysis."""

import csv
import io
import json

from simledge.analysis import spending_by_category, monthly_summary


def _get_transactions(conn, month):
    rows = conn.execute(
        "SELECT t.posted, t.description, COALESCE(t.category, 'uncategorized'),"
        " t.amount, a.name as account_name"
        " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        " WHERE strftime('%Y-%m', t.posted) = ?"
        " ORDER BY t.posted DESC",
        (month,),
    ).fetchall()
    return [{"date": r[0], "description": r[1], "category": r[2],
             "amount": r[3], "account": r[4]} for r in rows]


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
        lines.append(f"| {t['date']} | {t['description']} | {t['category']}"
                     f" | ${t['amount']:+,.2f} | {t['account']} |")

    return "\n".join(lines)


def export_csv(conn, month):
    transactions = _get_transactions(conn, month)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "description", "category", "amount", "account"])
    writer.writeheader()
    writer.writerows(transactions)
    return output.getvalue()


def export_json(conn, month):
    summary = monthly_summary(conn, month)
    categories = spending_by_category(conn, month)
    transactions = _get_transactions(conn, month)
    return json.dumps({
        "month": month,
        "summary": summary,
        "categories": categories,
        "transactions": transactions,
    }, indent=2)
