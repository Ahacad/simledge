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
"""


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
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
        " ON CONFLICT(id) DO UPDATE SET name=excluded.name, currency=excluded.currency, type=excluded.type",
        (id, institution_id, name, currency, type),
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


def upsert_transaction(conn, id, account_id, posted, amount, description,
                       category=None, pending=False, raw_json=None):
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
        "INSERT INTO sync_log (accounts_updated, transactions_added, status)"
        " VALUES (?, ?, ?)",
        (accounts_updated, transactions_added, status),
    )
    conn.commit()


def get_last_sync(conn):
    row = conn.execute(
        "SELECT synced_at FROM sync_log WHERE status='success' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None
