"""Tag CRUD operations for transaction tagging."""

from simledge.log import setup_logging

log = setup_logging("simledge.tags")


def create_tag(conn, name):
    """Insert a tag, return its id. Ignores if already exists."""
    name = name.strip().lower()
    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
    conn.commit()
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    return row[0]


def get_or_create_tag(conn, name):
    """Get existing tag id or create new one."""
    name = name.strip().lower()
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    return create_tag(conn, name)


def list_tags(conn):
    """Return all tags as [{"id", "name"}]."""
    rows = conn.execute("SELECT id, name FROM tags ORDER BY name").fetchall()
    return [{"id": r[0], "name": r[1]} for r in rows]


def tag_transaction(conn, txn_id, tag_name):
    """Tag a transaction. Idempotent."""
    tag_id = get_or_create_tag(conn, tag_name)
    conn.execute(
        "INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id)"
        " VALUES (?, ?)",
        (txn_id, tag_id),
    )
    conn.commit()


def untag_transaction(conn, txn_id, tag_name):
    """Remove a tag from a transaction."""
    tag_name = tag_name.strip().lower()
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
    if not row:
        return
    conn.execute(
        "DELETE FROM transaction_tags WHERE transaction_id = ? AND tag_id = ?",
        (txn_id, row[0]),
    )
    conn.commit()


def get_transaction_tags(conn, txn_id):
    """Return list of tag names for a transaction."""
    rows = conn.execute(
        "SELECT t.name FROM tags t"
        " JOIN transaction_tags tt ON t.id = tt.tag_id"
        " WHERE tt.transaction_id = ?"
        " ORDER BY t.name",
        (txn_id,),
    ).fetchall()
    return [r[0] for r in rows]


def set_transaction_tags(conn, txn_id, tag_names):
    """Replace all tags on a transaction."""
    conn.execute(
        "DELETE FROM transaction_tags WHERE transaction_id = ?", (txn_id,)
    )
    for name in tag_names:
        name = name.strip()
        if name:
            tag_id = get_or_create_tag(conn, name)
            conn.execute(
                "INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id)"
                " VALUES (?, ?)",
                (txn_id, tag_id),
            )
    conn.commit()


def delete_tag(conn, tag_id):
    """Delete a tag and all its associations."""
    conn.execute("DELETE FROM transaction_tags WHERE tag_id = ?", (tag_id,))
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
