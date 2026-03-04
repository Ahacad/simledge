"""Watchlist CRUD and spending queries."""

from datetime import date
import calendar

from simledge.analysis import _account_filter
from simledge.log import setup_logging

log = setup_logging("simledge.watchlist")


def create_watchlist(conn, name, monthly_target=None, filter_category=None,
                     filter_tag=None, filter_description=None):
    if not any([filter_category, filter_tag, filter_description]):
        raise ValueError("at least one filter is required")
    conn.execute(
        "INSERT INTO watchlists (name, monthly_target, filter_category,"
        " filter_tag, filter_description) VALUES (?, ?, ?, ?, ?)",
        (name, monthly_target, filter_category, filter_tag, filter_description),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_watchlists(conn):
    rows = conn.execute(
        "SELECT id, name, monthly_target, filter_category, filter_tag,"
        " filter_description, created_at FROM watchlists ORDER BY id"
    ).fetchall()
    return [
        {
            "id": r[0], "name": r[1], "monthly_target": r[2],
            "filter_category": r[3], "filter_tag": r[4],
            "filter_description": r[5], "created_at": r[6],
        }
        for r in rows
    ]


def update_watchlist(conn, watchlist_id, **kwargs):
    allowed = {"name", "monthly_target", "filter_category", "filter_tag",
               "filter_description"}
    updates, params = [], []
    for key, val in kwargs.items():
        if key not in allowed:
            continue
        updates.append(f"{key} = ?")
        params.append(val)
    if not updates:
        return
    params.append(watchlist_id)
    conn.execute(
        f"UPDATE watchlists SET {', '.join(updates)} WHERE id = ?", params
    )
    conn.commit()


def delete_watchlist(conn, watchlist_id):
    conn.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
    conn.commit()


def watchlist_spending(conn, watchlist_id, month, account_ids=None):
    row = conn.execute(
        "SELECT id, name, monthly_target, filter_category, filter_tag,"
        " filter_description FROM watchlists WHERE id = ?",
        (watchlist_id,),
    ).fetchone()
    if not row:
        return None

    wl_id, name, target, fcat, ftag, fdesc = row

    # Build dynamic query
    conditions = ["strftime('%Y-%m', t.posted) = ?", "t.amount < 0"]
    params = [month]

    acct_filt, acct_params = _account_filter(account_ids, table_prefix="t.")
    if acct_filt:
        conditions.append(acct_filt.lstrip(" AND "))
        params.extend(acct_params)

    if fcat:
        conditions.append("LOWER(t.category) LIKE LOWER(?)")
        params.append(fcat)

    if fdesc:
        conditions.append("LOWER(t.description) LIKE LOWER(?)")
        params.append(fdesc)

    if ftag:
        conditions.append(
            "t.id IN (SELECT transaction_id FROM transaction_tags tt"
            " JOIN tags tg ON tt.tag_id = tg.id"
            " WHERE LOWER(tg.name) = LOWER(?))"
        )
        params.append(ftag)

    where = " AND ".join(conditions)
    result = conn.execute(
        f"SELECT COALESCE(SUM(t.amount), 0), COUNT(*)"
        f" FROM transactions t WHERE {where}",
        params,
    ).fetchone()

    actual = abs(result[0])
    txn_count = result[1]

    # Projection
    today = date.today()
    year, mon = int(month[:4]), int(month[5:])
    _, last_day = calendar.monthrange(year, mon)
    month_start = date(year, mon, 1)

    if today.strftime("%Y-%m") == month:
        days_elapsed = (today - month_start).days + 1
    elif today > date(year, mon, last_day):
        days_elapsed = last_day
    else:
        days_elapsed = 0

    if days_elapsed > 0:
        projected = actual * (last_day / days_elapsed)
    else:
        projected = 0

    remaining = (target - actual) if target is not None else None
    pct_used = (actual / target * 100) if target else None
    on_track = (projected <= target) if target is not None else None

    return {
        "id": wl_id,
        "name": name,
        "monthly_target": target,
        "actual": actual,
        "remaining": remaining,
        "pct_used": round(pct_used, 1) if pct_used is not None else None,
        "transaction_count": txn_count,
        "projected_month_end": round(projected, 2),
        "on_track": on_track,
    }


def all_watchlist_spending(conn, month, account_ids=None):
    watchlists = get_watchlists(conn)
    return [
        watchlist_spending(conn, w["id"], month, account_ids=account_ids)
        for w in watchlists
    ]
