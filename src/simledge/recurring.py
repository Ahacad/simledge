"""Detect recurring transactions from transaction history."""

import re
import statistics
from datetime import datetime, timedelta

from simledge.log import setup_logging

log = setup_logging("simledge.recurring")


def _normalize_description(desc):
    """Lowercase, collapse whitespace, strip trailing digits/IDs."""
    if not desc:
        return ""
    s = desc.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    # Strip trailing transaction IDs / reference numbers (e.g. "#12345", "00839")
    s = re.sub(r'\s*#?\d{3,}$', '', s)
    return s.strip()


def _classify_frequency(avg_days):
    """Classify average interval into a frequency label."""
    if 5 <= avg_days <= 9:
        return "weekly"
    if 25 <= avg_days <= 35:
        return "monthly"
    if 350 <= avg_days <= 380:
        return "yearly"
    return None


def detect_recurring(conn, min_occurrences=3, tolerance_days=5,
                     tolerance_amount=0.10):
    """Detect recurring transactions from the database.

    Returns list of dicts with: description, category, frequency,
    avg_amount, last_amount, last_date, next_expected,
    occurrence_count, is_fixed_amount, account.
    """
    rows = conn.execute(
        "SELECT t.posted, t.amount, t.description, t.category, a.name"
        " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        " WHERE t.pending = 0"
        " ORDER BY t.posted ASC"
    ).fetchall()

    # Group by normalized description
    groups = {}
    for posted, amount, desc, category, account in rows:
        key = _normalize_description(desc)
        if not key:
            continue
        groups.setdefault(key, []).append({
            "posted": posted,
            "amount": amount,
            "description": desc,
            "category": category,
            "account": account,
        })

    results = []
    for key, txns in groups.items():
        if len(txns) < min_occurrences:
            continue

        # Parse dates and sort
        dated = []
        for t in txns:
            try:
                dt = datetime.strptime(t["posted"][:10], "%Y-%m-%d")
                dated.append((dt, t))
            except (ValueError, TypeError):
                continue

        if len(dated) < min_occurrences:
            continue

        dated.sort(key=lambda x: x[0])

        # Calculate intervals between consecutive transactions
        intervals = []
        for i in range(1, len(dated)):
            delta = (dated[i][0] - dated[i - 1][0]).days
            intervals.append(delta)

        if not intervals:
            continue

        avg_interval = statistics.mean(intervals)
        frequency = _classify_frequency(avg_interval)
        if not frequency:
            continue

        # Check interval consistency
        if len(intervals) > 1:
            interval_std = statistics.stdev(intervals)
            if interval_std > tolerance_days * 2:
                continue

        # Check amount consistency
        amounts = [abs(t["amount"]) for _, t in dated]
        avg_amount = statistics.mean(amounts)
        is_fixed = True
        if avg_amount > 0 and len(amounts) > 1:
            amount_std = statistics.stdev(amounts)
            is_fixed = (amount_std / avg_amount) < tolerance_amount

        last_dt, last_txn = dated[-1]
        next_expected = last_dt + timedelta(days=round(avg_interval))

        results.append({
            "description": last_txn["description"],
            "category": last_txn["category"],
            "frequency": frequency,
            "avg_amount": last_txn["amount"],
            "last_amount": last_txn["amount"],
            "last_date": last_txn["posted"][:10],
            "next_expected": next_expected.strftime("%Y-%m-%d"),
            "occurrence_count": len(dated),
            "is_fixed_amount": is_fixed,
            "account": last_txn["account"],
        })

    # Sort by next_expected
    results.sort(key=lambda r: r["next_expected"])
    log.debug("detected %d recurring transactions", len(results))
    return results
