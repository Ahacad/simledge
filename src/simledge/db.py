"""SQLite schema, initialization, and data access."""

import sqlite3

from simledge.log import setup_logging

log = setup_logging("simledge.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS institutions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    institution_id TEXT REFERENCES institutions(id),
    name TEXT NOT NULL,
    currency TEXT DEFAULT 'USD',
    type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS balances (
    account_id TEXT REFERENCES accounts(id),
    date TEXT NOT NULL,
    balance REAL NOT NULL,
    available_balance REAL,
    PRIMARY KEY (account_id, date)
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT REFERENCES accounts(id),
    posted TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    category TEXT,
    pending INTEGER DEFAULT 0,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS category_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    category TEXT NOT NULL,
    priority INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at TEXT DEFAULT (datetime('now')),
    accounts_updated INTEGER,
    transactions_added INTEGER,
    status TEXT
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL UNIQUE,
    monthly_limit REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS transaction_tags (
    transaction_id TEXT REFERENCES transactions(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (transaction_id, tag_id)
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    target_date TEXT,
    account_id TEXT REFERENCES accounts(id),
    starting_balance REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monthly_target REAL,
    filter_category TEXT,
    filter_tag TEXT,
    filter_description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    # Migration: add notes column if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    if "notes" not in cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN notes TEXT")
    # Migration: add display_name column to accounts if missing
    acct_cols = {r[1] for r in conn.execute("PRAGMA table_info(accounts)").fetchall()}
    if "display_name" not in acct_cols:
        conn.execute("ALTER TABLE accounts ADD COLUMN display_name TEXT")
    conn.commit()
    log.debug("database initialized at %s", db_path)
    return conn


def upsert_institution(conn, id, name, domain=None):
    conn.execute(
        "INSERT INTO institutions (id, name, domain) VALUES (?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET name=excluded.name, domain=excluded.domain",
        (id, name, domain),
    )
    conn.commit()


def upsert_account(conn, id, institution_id, name, currency="USD", type=None):
    conn.execute(
        "INSERT INTO accounts (id, institution_id, name, currency, type) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET name=excluded.name, currency=excluded.currency,"
        " type=COALESCE(excluded.type, accounts.type)",
        (id, institution_id, name, currency, type),
    )
    conn.commit()


def update_account_display_name(conn, account_id, display_name):
    conn.execute(
        "UPDATE accounts SET display_name = ? WHERE id = ?",
        (display_name or None, account_id),
    )
    conn.commit()


def snapshot_balance(conn, account_id, date, balance, available_balance=None):
    conn.execute(
        "INSERT INTO balances (account_id, date, balance, available_balance) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(account_id, date) DO UPDATE SET balance=excluded.balance,"
        " available_balance=excluded.available_balance",
        (account_id, date, balance, available_balance),
    )
    conn.commit()


def upsert_transaction(
    conn, id, account_id, posted, amount, description, category=None, pending=False, raw_json=None
):
    conn.execute(
        "INSERT INTO transactions (id, account_id, posted, amount, description,"
        " category, pending, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET description=excluded.description,"
        " amount=excluded.amount, category=excluded.category,"
        " pending=excluded.pending, raw_json=excluded.raw_json",
        (id, account_id, posted, amount, description, category, int(pending), raw_json),
    )
    conn.commit()


def log_sync(conn, accounts_updated, transactions_added, status="success"):
    conn.execute(
        "INSERT INTO sync_log (accounts_updated, transactions_added, status) VALUES (?, ?, ?)",
        (accounts_updated, transactions_added, status),
    )
    conn.commit()


def get_last_sync(conn):
    row = conn.execute(
        "SELECT synced_at FROM sync_log WHERE status='success' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


EDITABLE_TXN_FIELDS = {"category", "notes"}


def update_transaction_field(conn, txn_id, field, value):
    if field not in EDITABLE_TXN_FIELDS:
        raise ValueError(f"field {field!r} is not editable")
    conn.execute(
        f"UPDATE transactions SET {field} = ? WHERE id = ?",
        (value, txn_id),
    )
    conn.commit()


def get_transaction(conn, txn_id):
    row = conn.execute(
        "SELECT t.id, t.posted, t.amount, t.description, t.category, t.notes,"
        " t.pending, a.name, i.name"
        " FROM transactions t"
        " JOIN accounts a ON t.account_id = a.id"
        " LEFT JOIN institutions i ON a.institution_id = i.id"
        " WHERE t.id = ?",
        (txn_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "posted": row[1],
        "amount": row[2],
        "description": row[3],
        "category": row[4] or "",
        "notes": row[5] or "",
        "pending": bool(row[6]),
        "account": row[7],
        "institution": row[8] or "",
    }
