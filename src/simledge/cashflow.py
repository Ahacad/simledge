"""Projected cash flow using recurring transactions."""

from collections import defaultdict
from datetime import date, timedelta

from simledge.analysis import account_summary
from simledge.log import setup_logging
from simledge.recurring import detect_recurring, generate_occurrences

log = setup_logging("simledge.cashflow")


def project_balances(conn, days=90, account_ids=None):
    """Project future balances using detected recurring transactions.

    Returns dict with daily_totals, per_account, negative_dates, summary.
    """
    accounts = account_summary(conn, account_ids=account_ids)
    recurring = detect_recurring(conn)

    if account_ids:
        account_names = {a["name"] for a in accounts}
        recurring = [r for r in recurring if r["account"] in account_names]

    today = date.today()
    end = today + timedelta(days=days)

    # Build account balance map: name -> {id, balance}
    acct_map = {}
    for a in accounts:
        acct_map[a["name"]] = {
            "id": a["id"],
            "balance": a["balance"] or 0,
        }

    # Generate all future occurrences
    all_occurrences = []
    for item in recurring:
        occs = generate_occurrences(item, today, end)
        all_occurrences.extend(occs)

    # Group occurrences by date and account
    by_date_account = defaultdict(lambda: defaultdict(float))
    for occ in all_occurrences:
        by_date_account[occ["date"]][occ["account"]] += occ["amount"]

    # Build daily running balances per account
    cc_accounts = {a["name"] for a in accounts if a.get("type") in ("credit", "credit_card")}
    balances = {name: info["balance"] for name, info in acct_map.items()}
    per_account_daily = {name: [] for name in acct_map}
    daily_totals = []
    negative_dates = {}

    for day_offset in range(days + 1):
        d = today + timedelta(days=day_offset)
        d_str = d.strftime("%Y-%m-%d")

        # Apply transactions for this day
        if d_str in by_date_account:
            for acct_name, amount in by_date_account[d_str].items():
                if acct_name in balances:
                    balances[acct_name] += amount

        # Record per-account
        for name in acct_map:
            bal = balances[name]
            per_account_daily[name].append({"date": d_str, "balance": bal})
            # Track first negative date per account
            if bal < 0 and name not in negative_dates and name not in cc_accounts:
                negative_dates[name] = {"date": d_str, "account": name, "balance": bal}

        # Record total
        total = sum(balances.values())
        daily_totals.append({"date": d_str, "projected_balance": total})

    # Build per_account result
    per_account = []
    for name, info in acct_map.items():
        per_account.append(
            {
                "account": name,
                "account_id": info["id"],
                "current_balance": info["balance"],
                "daily": per_account_daily[name],
            }
        )

    # Summary
    def balance_at_day(day_num):
        idx = min(day_num, len(daily_totals) - 1)
        return daily_totals[idx]["projected_balance"]

    current_total = daily_totals[0]["projected_balance"] if daily_totals else 0
    summary = {
        "current_total": current_total,
        "projected_30d": balance_at_day(30),
        "projected_60d": balance_at_day(60),
        "projected_90d": balance_at_day(90),
    }

    return {
        "daily_totals": daily_totals,
        "per_account": per_account,
        "negative_dates": list(negative_dates.values()),
        "summary": summary,
    }
