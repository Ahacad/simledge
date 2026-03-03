"""Category rule engine — regex/keyword matching for transactions."""

import re

from simledge.log import setup_logging

log = setup_logging("simledge.categorize")


def add_rule(conn, pattern, category, priority=0):
    conn.execute(
        "INSERT INTO category_rules (pattern, category, priority) VALUES (?, ?, ?)",
        (pattern, category, priority),
    )
    conn.commit()


def list_rules(conn):
    rows = conn.execute(
        "SELECT id, pattern, category, priority FROM category_rules ORDER BY priority DESC, id"
    ).fetchall()
    return [{"id": r[0], "pattern": r[1], "category": r[2], "priority": r[3]} for r in rows]


def delete_rule(conn, rule_id):
    conn.execute("DELETE FROM category_rules WHERE id = ?", (rule_id,))
    conn.commit()


def apply_rules(conn, dry_run=False):
    """Apply category rules to uncategorized transactions. Returns count of categorized."""
    rules = conn.execute(
        "SELECT pattern, category FROM category_rules ORDER BY priority DESC, id"
    ).fetchall()

    uncategorized = conn.execute(
        "SELECT id, description FROM transactions WHERE category IS NULL"
    ).fetchall()

    count = 0
    for txn_id, description in uncategorized:
        for pattern, category in rules:
            try:
                if re.search(pattern, description, re.IGNORECASE):
                    if not dry_run:
                        conn.execute(
                            "UPDATE transactions SET category = ? WHERE id = ?",
                            (category, txn_id),
                        )
                    count += 1
                    break
            except re.error:
                # Fall back to substring match if invalid regex
                if pattern.upper() in description.upper():
                    if not dry_run:
                        conn.execute(
                            "UPDATE transactions SET category = ? WHERE id = ?",
                            (category, txn_id),
                        )
                    count += 1
                    break

    if not dry_run:
        conn.commit()
    log.info("categorized %d transactions (dry_run=%s)", count, dry_run)
    return count
