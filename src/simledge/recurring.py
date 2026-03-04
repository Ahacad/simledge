"""Detect recurring transactions from transaction history."""

import calendar as cal_mod
import re
import statistics
from datetime import date, datetime, timedelta

from simledge.log import setup_logging

log = setup_logging("simledge.recurring")


def _normalize_description(desc):
    """Lowercase, collapse whitespace, strip trailing digits/IDs."""
    if not desc:
        return ""
    s = desc.lower().strip()
    s = re.sub(r"\s+", " ", s)
    # Strip trailing transaction IDs / reference numbers (e.g. "#12345", "00839")
    s = re.sub(r"\s*#?\d{3,}$", "", s)
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


def detect_recurring(conn, min_occurrences=3, tolerance_days=5, tolerance_amount=0.10):
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
        groups.setdefault(key, []).append(
            {
                "posted": posted,
                "amount": amount,
                "description": desc,
                "category": category,
                "account": account,
            }
        )

    results = []
    for _key, txns in groups.items():
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

        results.append(
            {
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
            }
        )

    # Sort by next_expected
    results.sort(key=lambda r: r["next_expected"])
    log.debug("detected %d recurring transactions", len(results))
    return results


_FREQ_DAYS = {"weekly": 7, "monthly": 30, "yearly": 365}


def generate_occurrences(recurring_item, start_date, end_date):
    """Generate expected occurrences of a recurring transaction within a date range.

    Returns list of dicts with date, amount, description, account.
    """
    freq = recurring_item.get("frequency", "monthly")
    interval = _FREQ_DAYS.get(freq, 30)

    next_str = recurring_item.get("next_expected", "")
    try:
        cursor = datetime.strptime(next_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    # Step forward if before start_date
    while cursor < start_date:
        cursor += timedelta(days=interval)

    occurrences = []
    while cursor <= end_date:
        occurrences.append(
            {
                "date": cursor.strftime("%Y-%m-%d"),
                "amount": recurring_item.get("last_amount", 0),
                "description": recurring_item.get("description", ""),
                "account": recurring_item.get("account", ""),
            }
        )
        cursor += timedelta(days=interval)

    return occurrences


def check_bill_paid(conn, description, expected_amount, expected_date, tolerance_days=5):
    """Check if a matching transaction exists near the expected date.

    Returns dict with paid, actual_date, actual_amount.
    """
    norm_desc = _normalize_description(description)
    rows = conn.execute(
        "SELECT t.posted, t.amount, t.description"
        " FROM transactions t"
        " WHERE t.pending = 0"
        " ORDER BY t.posted DESC"
    ).fetchall()

    best = None
    best_dist = None
    for posted, amount, desc in rows:
        if _normalize_description(desc) != norm_desc:
            continue
        if expected_amount != 0 and abs(amount - expected_amount) > abs(expected_amount) * 0.10:
            continue
        try:
            txn_date = datetime.strptime(posted[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if isinstance(expected_date, str):
            expected_date = datetime.strptime(expected_date, "%Y-%m-%d").date()
        dist = abs((txn_date - expected_date).days)
        if dist > tolerance_days:
            continue
        if best is None or dist < best_dist:
            best = {"paid": True, "actual_date": posted[:10], "actual_amount": amount}
            best_dist = dist

    if best:
        return best
    return {"paid": False, "actual_date": None, "actual_amount": None}


def calendar_bills(conn, month):
    """Return all expected bill occurrences for a given YYYY-MM month with status.

    Returns list sorted by date with date, day, weekday, description,
    expected_amount, status, actual_amount, account.
    """
    year, mon = int(month[:4]), int(month[5:7])
    month_start = date(year, mon, 1)
    last_day = cal_mod.monthrange(year, mon)[1]
    month_end = date(year, mon, last_day)
    today = date.today()

    recurring = detect_recurring(conn)
    results = []

    for item in recurring:
        occs = generate_occurrences(item, month_start, month_end)
        for occ in occs:
            occ_date = datetime.strptime(occ["date"], "%Y-%m-%d").date()
            paid_info = check_bill_paid(conn, occ["description"], occ["amount"], occ_date)

            if paid_info["paid"]:
                status = "paid"
            elif occ_date < today:
                status = "overdue"
            else:
                status = "upcoming"

            results.append(
                {
                    "date": occ["date"],
                    "day": occ_date.day,
                    "weekday": occ_date.weekday(),
                    "description": occ["description"],
                    "expected_amount": occ["amount"],
                    "status": status,
                    "actual_amount": paid_info["actual_amount"],
                    "account": occ["account"],
                }
            )

    results.sort(key=lambda r: r["date"])
    return results
