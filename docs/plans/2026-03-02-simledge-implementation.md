# SimpLedge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal finance TUI tool that syncs bank data via SimpleFIN, stores in SQLite, and provides interactive dashboards.

**Architecture:** Monolith CLI+TUI. Single Python package with `uv`/hatchling. CLI subcommands for sync/export/rules. Textual TUI as the primary interface. All data in a single SQLite file.

**Tech Stack:** Python 3.11+, uv, hatchling, textual, httpx, plotext, sqlite3 (stdlib), tomllib (stdlib)

**Design doc:** `docs/plans/2026-03-02-simledge-design.md`

---

### Task 1: Project scaffolding and packaging

**Files:**
- Create: `pyproject.toml`
- Create: `src/simledge/__init__.py`
- Create: `src/simledge/cli.py`
- Create: `tests/__init__.py`
- Create: `CLAUDE.md`
- Create: `.gitignore`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "simledge"
version = "0.1.0"
description = "Personal finance TUI — SimpleFIN sync, SQLite storage, interactive dashboards"
readme = "README.md"
license = "MIT"
authors = [
    { name = "ahacad", email = "ahacadev@gmail.com" }
]
requires-python = ">=3.11"
dependencies = [
    "textual>=1.0",
    "httpx>=0.27",
    "plotext>=5.3",
]

[project.scripts]
simledge = "simledge.cli:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "textual-dev>=1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Create src/simledge/__init__.py**

```python
"""SimpLedge — personal finance TUI."""
```

**Step 3: Create minimal cli.py**

```python
"""CLI entry point for SimpLedge."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="simledge",
        description="Personal finance TUI — sync, analyze, export",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="fetch data from SimpleFIN")
    sub.add_parser("status", help="show last sync and DB stats")
    sub.add_parser("setup", help="configure SimpleFIN access")

    export_p = sub.add_parser("export", help="export data for analysis")
    export_p.add_argument("--month", help="YYYY-MM")
    export_p.add_argument("--format", choices=["markdown", "csv", "json"], default="markdown")

    rule_p = sub.add_parser("rule", help="manage category rules")
    rule_sub = rule_p.add_subparsers(dest="rule_command")
    add_p = rule_sub.add_parser("add", help="add a category rule")
    add_p.add_argument("pattern", help="regex or keyword to match")
    add_p.add_argument("category", help="category to assign")
    rule_sub.add_parser("list", help="list all rules")
    rule_sub.add_parser("test", help="dry-run rules against uncategorized")

    args = parser.parse_args()

    if args.command is None:
        # Default: launch TUI
        print("TUI not implemented yet — use a subcommand. Try: simledge --help")
        sys.exit(0)

    print(f"Command '{args.command}' not implemented yet.")


if __name__ == "__main__":
    main()
```

**Step 4: Create .gitignore**

```
__pycache__/
*.pyc
*.egg-info/
dist/
.venv/
*.db
```

**Step 5: Create CLAUDE.md**

Model it after the stt project's CLAUDE.md. Include project layout, conventions, commands. This will be fleshed out as we build.

```markdown
# SimpLedge — Personal Finance TUI

## What This Is

Personal finance data tool. Syncs bank/card/investment data via SimpleFIN, stores locally in SQLite, provides structured analysis through a Textual TUI dashboard.

## Architecture

Monolith CLI+TUI. Single Python package, one entry point (`simledge`).

```
SimpleFIN API → simledge sync → SQLite → simledge TUI
                                       → simledge export → Claude Code
```

## Tech Stack

- Python 3.11+, `uv` package manager, hatchling build
- textual (TUI), httpx (HTTP), plotext (charts)
- SQLite (stdlib), tomllib (stdlib)
- pytest for testing

## Commands

```bash
uv tool install -e .           # install (dev)
uv tool install -e . --force   # update after changes
pytest                         # run tests
simledge                       # launch TUI
simledge sync                  # fetch from SimpleFIN
simledge export                # export for AI analysis
```

## Project Layout

```
src/simledge/
  cli.py          # argparse dispatcher
  config.py       # constants, paths
  compat.py       # platform detection, XDG dirs
  db.py           # SQLite schema, migrations, queries
  sync.py         # SimpleFIN client
  categorize.py   # rule engine
  analysis.py     # structured queries
  export.py       # data export
  log.py          # logging setup
  tui/
    app.py        # Textual App
    screens/      # dashboard screens
    widgets/      # reusable widgets
tests/            # pytest unit tests
```

## Code Conventions

### Style
- snake_case functions/variables, UPPER_CASE module constants
- Self-documenting names over comments
- No type annotations unless they clarify ambiguity
- ~80-100 char lines, flexible
- No dead code, no commented-out blocks

### Patterns
- Constants centralized in `config.py`
- `log = setup_logging("simledge.module")` at module top
- Error handling at boundaries only
- Graceful degradation for UX

### Commits
- Auto-commit after each logical chunk
- Conventional Commits: `type(scope): description`
- Run `pytest` before committing

## Testing

```bash
pytest              # all tests
pytest -x           # stop on first failure
pytest -v           # verbose
```

- File per module: `test_db.py` tests `db.py`
- Mock external deps (httpx, filesystem)
- Use `tmp_path` for temp files
- Test behavior, not implementation
```

**Step 6: Create tests/__init__.py**

Empty file.

**Step 7: Install and verify**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && uv tool install -e .`
Run: `simledge --help`
Expected: help text with subcommands listed

**Step 8: Commit**

```bash
git add pyproject.toml src/ tests/ CLAUDE.md .gitignore
git commit -m "feat: scaffold project with CLI entry point and packaging"
```

---

### Task 2: Config and platform compatibility

**Files:**
- Create: `src/simledge/compat.py`
- Create: `src/simledge/config.py`
- Create: `src/simledge/log.py`
- Create: `tests/test_config.py`

**Step 1: Write failing test for config paths**

```python
# tests/test_config.py
from unittest.mock import patch
import os


def test_data_dir_returns_xdg_path():
    with patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/test-xdg"}):
        from importlib import reload
        import simledge.compat
        reload(simledge.compat)
        result = simledge.compat.data_dir()
        assert result == "/tmp/test-xdg/simledge"


def test_config_dir_returns_xdg_path():
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/test-xdg-config"}):
        from importlib import reload
        import simledge.compat
        reload(simledge.compat)
        result = simledge.compat.config_dir()
        assert result == "/tmp/test-xdg-config/simledge"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_config.py -v`
Expected: FAIL — module not found

**Step 3: Implement compat.py**

```python
"""Platform detection and path helpers."""

import os
import sys

LINUX = sys.platform == "linux"
WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"


def data_dir():
    if WINDOWS:
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "simledge")
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "simledge")


def config_dir():
    if WINDOWS:
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "simledge")
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "simledge")
```

**Step 4: Implement config.py**

```python
"""Shared constants and paths for SimpLedge."""

import os

from simledge.compat import data_dir, config_dir

# Paths
DATA_DIR = data_dir()
CONFIG_DIR = config_dir()
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "simledge.db")
LOG_DIR = DATA_DIR
LOG_PATH = os.path.join(DATA_DIR, "simledge.log")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.toml")
```

**Step 5: Implement log.py**

```python
"""Logging setup for SimpLedge."""

import logging
import os

from simledge.config import LOG_DIR, LOG_PATH


def setup_logging(name):
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    fh = logging.FileHandler(LOG_PATH)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger
```

**Step 6: Run tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_config.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/simledge/compat.py src/simledge/config.py src/simledge/log.py tests/test_config.py
git commit -m "feat(config): add platform paths, config constants, and logging"
```

---

### Task 3: Database schema and migrations

**Files:**
- Create: `src/simledge/db.py`
- Create: `tests/test_db.py`

**Step 1: Write failing tests for DB initialization**

```python
# tests/test_db.py
import sqlite3
import os


def test_init_db_creates_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db
    conn = init_db(db_path)

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    assert "institutions" in tables
    assert "accounts" in tables
    assert "balances" in tables
    assert "transactions" in tables
    assert "category_rules" in tables
    assert "sync_log" in tables
    conn.close()


def test_init_db_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db
    conn1 = init_db(db_path)
    conn1.close()
    conn2 = init_db(db_path)
    cursor = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert len(tables) >= 6
    conn2.close()


def test_upsert_institution(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase Bank", "chase.com")
    upsert_institution(conn, "chase-1", "Chase", "chase.com")  # update name

    row = conn.execute("SELECT name FROM institutions WHERE id = ?", ("chase-1",)).fetchone()
    assert row[0] == "Chase"
    conn.close()


def test_upsert_account(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution, upsert_account
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    row = conn.execute("SELECT name, type FROM accounts WHERE id = ?", ("acct-1",)).fetchone()
    assert row[0] == "Checking"
    assert row[1] == "checking"
    conn.close()


def test_upsert_transaction_dedup(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", pending=False, raw_json='{}')
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS #123", pending=False, raw_json='{}')

    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 1
    # Description updated on second upsert
    desc = conn.execute("SELECT description FROM transactions WHERE id = ?", ("txn-1",)).fetchone()[0]
    assert desc == "WHOLE FOODS #123"
    conn.close()


def test_snapshot_balance(tmp_path):
    db_path = str(tmp_path / "test.db")
    from simledge.db import init_db, upsert_institution, upsert_account, snapshot_balance
    conn = init_db(db_path)
    upsert_institution(conn, "chase-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "chase-1", "Checking", "USD", "checking")

    snapshot_balance(conn, "acct-1", "2026-03-01", 4230.50, 4200.00)
    snapshot_balance(conn, "acct-1", "2026-03-01", 4235.00, 4205.00)  # replace same day

    row = conn.execute("SELECT balance FROM balances WHERE account_id = ? AND date = ?",
                       ("acct-1", "2026-03-01")).fetchone()
    assert row[0] == 4235.00
    conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_db.py -v`
Expected: FAIL — import error

**Step 3: Implement db.py**

```python
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
```

**Step 4: Run tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_db.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/simledge/db.py tests/test_db.py
git commit -m "feat(db): add SQLite schema with upsert helpers and balance snapshots"
```

---

### Task 4: SimpleFIN sync client

**Files:**
- Create: `src/simledge/sync.py`
- Create: `tests/test_sync.py`

**Step 1: Write failing tests for sync**

```python
# tests/test_sync.py
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


SAMPLE_RESPONSE = {
    "accounts": [
        {
            "org": {"domain": "chase.com", "name": "Chase", "id": "chase-org-1"},
            "id": "acct-checking-1",
            "name": "TOTAL CHECKING",
            "currency": "USD",
            "balance": "4230.50",
            "available-balance": "4200.00",
            "balance-date": 1740873600,
            "transactions": [
                {
                    "id": "txn-1",
                    "posted": 1740787200,
                    "amount": "-47.32",
                    "description": "WHOLE FOODS MKT #10234",
                    "pending": False,
                },
                {
                    "id": "txn-2",
                    "posted": 1740700800,
                    "amount": "4225.00",
                    "description": "PAYROLL AMAZON",
                    "pending": False,
                },
            ],
        }
    ]
}


def test_parse_simplefin_response():
    from simledge.sync import parse_response
    institutions, accounts, balances, transactions = parse_response(SAMPLE_RESPONSE)

    assert len(institutions) == 1
    assert institutions[0]["id"] == "chase-org-1"
    assert institutions[0]["name"] == "Chase"

    assert len(accounts) == 1
    assert accounts[0]["id"] == "acct-checking-1"
    assert accounts[0]["name"] == "TOTAL CHECKING"
    assert accounts[0]["institution_id"] == "chase-org-1"

    assert len(balances) == 1
    assert balances[0]["balance"] == 4230.50

    assert len(transactions) == 2
    assert transactions[0]["amount"] == -47.32
    assert transactions[1]["amount"] == 4225.00


def test_parse_handles_missing_org():
    response = {
        "accounts": [
            {
                "id": "acct-1",
                "name": "Account",
                "currency": "USD",
                "balance": "100.00",
                "balance-date": 1740873600,
                "transactions": [],
            }
        ]
    }
    from simledge.sync import parse_response
    institutions, accounts, balances, transactions = parse_response(response)
    assert len(institutions) == 0
    assert accounts[0]["institution_id"] is None


def test_parse_handles_pending_transactions():
    response = {
        "accounts": [
            {
                "id": "acct-1",
                "name": "Account",
                "currency": "USD",
                "balance": "100.00",
                "balance-date": 1740873600,
                "transactions": [
                    {
                        "id": "txn-pending",
                        "posted": 1740787200,
                        "amount": "-10.00",
                        "description": "PENDING CHARGE",
                        "pending": True,
                    }
                ],
            }
        ]
    }
    from simledge.sync import parse_response
    _, _, _, transactions = parse_response(response)
    assert transactions[0]["pending"] is True
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_sync.py -v`
Expected: FAIL

**Step 3: Implement sync.py**

```python
"""SimpleFIN API client and data sync."""

import json
from base64 import b64decode
from datetime import datetime, timezone

import httpx

from simledge.config import DB_PATH, CONFIG_PATH
from simledge.db import (
    init_db, upsert_institution, upsert_account, snapshot_balance,
    upsert_transaction, log_sync, get_last_sync,
)
from simledge.log import setup_logging

log = setup_logging("simledge.sync")


def parse_response(data):
    """Parse SimpleFIN JSON response into normalized records."""
    institutions = []
    accounts = []
    balances = []
    transactions = []
    seen_orgs = set()

    for acct in data.get("accounts", []):
        org = acct.get("org")
        institution_id = None

        if org and org.get("id"):
            institution_id = org["id"]
            if institution_id not in seen_orgs:
                institutions.append({
                    "id": institution_id,
                    "name": org.get("name", ""),
                    "domain": org.get("domain"),
                })
                seen_orgs.add(institution_id)

        accounts.append({
            "id": acct["id"],
            "institution_id": institution_id,
            "name": acct["name"],
            "currency": acct.get("currency", "USD"),
        })

        balance_ts = acct.get("balance-date", 0)
        balance_date = datetime.fromtimestamp(balance_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        balances.append({
            "account_id": acct["id"],
            "date": balance_date,
            "balance": float(acct.get("balance", 0)),
            "available_balance": float(acct["available-balance"]) if "available-balance" in acct else None,
        })

        for txn in acct.get("transactions", []):
            posted_ts = txn.get("posted", 0)
            posted_date = datetime.fromtimestamp(posted_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            transactions.append({
                "id": txn["id"],
                "account_id": acct["id"],
                "posted": posted_date,
                "amount": float(txn.get("amount", 0)),
                "description": txn.get("description", ""),
                "pending": txn.get("pending", False),
                "raw_json": json.dumps(txn),
            })

    return institutions, accounts, balances, transactions


async def fetch_accounts(access_url, start_date=None):
    """Fetch account data from SimpleFIN."""
    params = {"pending": "1"}
    if start_date:
        dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        params["start-date"] = str(int(dt.timestamp()))

    # access_url contains basic auth credentials
    async with httpx.AsyncClient() as client:
        resp = await client.get(access_url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()


def load_access_url():
    """Read SimpleFIN access URL from config."""
    import tomllib
    try:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
        return config["simplefin"]["access_url"]
    except (FileNotFoundError, KeyError) as e:
        log.error("config not found or missing simplefin.access_url: %s", e)
        return None


async def run_sync(full=False):
    """Main sync: fetch from SimpleFIN, update local DB."""
    access_url = load_access_url()
    if not access_url:
        print("No SimpleFIN access URL configured. Run: simledge setup")
        return

    conn = init_db(DB_PATH)
    start_date = None if full else get_last_sync(conn)

    log.info("syncing from SimpleFIN (start_date=%s, full=%s)", start_date, full)
    try:
        data = await fetch_accounts(access_url, start_date)
    except httpx.HTTPError as e:
        log.error("SimpleFIN request failed: %s", e)
        log_sync(conn, 0, 0, status=f"error: {e}")
        print(f"Sync failed: {e}")
        conn.close()
        return

    institutions, accounts, balances, transactions = parse_response(data)

    for inst in institutions:
        upsert_institution(conn, inst["id"], inst["name"], inst.get("domain"))
    for acct in accounts:
        upsert_account(conn, acct["id"], acct["institution_id"], acct["name"], acct["currency"])
    for bal in balances:
        snapshot_balance(conn, bal["account_id"], bal["date"], bal["balance"], bal.get("available_balance"))

    txn_count = 0
    for txn in transactions:
        upsert_transaction(
            conn, txn["id"], txn["account_id"], txn["posted"], txn["amount"],
            txn["description"], pending=txn["pending"], raw_json=txn["raw_json"],
        )
        txn_count += 1

    log_sync(conn, len(accounts), txn_count)
    print(f"Synced {len(accounts)} accounts, {txn_count} transactions")
    conn.close()
```

**Step 4: Run tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_sync.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/simledge/sync.py tests/test_sync.py
git commit -m "feat(sync): add SimpleFIN client with response parsing and DB sync"
```

---

### Task 5: Category rule engine

**Files:**
- Create: `src/simledge/categorize.py`
- Create: `tests/test_categorize.py`

**Step 1: Write failing tests**

```python
# tests/test_categorize.py

def test_apply_rules_matches_keyword(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    from simledge.categorize import add_rule, apply_rules

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT #123")
    upsert_transaction(conn, "txn-2", "acct-1", "2026-03-01", -23.99, "AMAZON.COM")

    add_rule(conn, "WHOLE FOODS", "groceries")
    add_rule(conn, "AMAZON", "shopping")
    count = apply_rules(conn)

    assert count == 2
    row1 = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row1[0] == "groceries"
    row2 = conn.execute("SELECT category FROM transactions WHERE id='txn-2'").fetchone()
    assert row2[0] == "shopping"
    conn.close()


def test_apply_rules_respects_priority(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    from simledge.categorize import add_rule, apply_rules

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS MKT")

    add_rule(conn, "WHOLE", "generic", priority=0)
    add_rule(conn, "WHOLE FOODS", "groceries", priority=10)
    apply_rules(conn)

    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] == "groceries"
    conn.close()


def test_apply_rules_skips_already_categorized(tmp_path):
    from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction
    from simledge.categorize import add_rule, apply_rules

    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Bank", None)
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "txn-1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS",
                       category="food")

    add_rule(conn, "WHOLE FOODS", "groceries")
    count = apply_rules(conn)

    assert count == 0
    row = conn.execute("SELECT category FROM transactions WHERE id='txn-1'").fetchone()
    assert row[0] == "food"  # unchanged
    conn.close()


def test_list_rules(tmp_path):
    from simledge.db import init_db
    from simledge.categorize import add_rule, list_rules

    conn = init_db(str(tmp_path / "test.db"))
    add_rule(conn, "AMAZON", "shopping", priority=0)
    add_rule(conn, "WHOLE FOODS", "groceries", priority=10)

    rules = list_rules(conn)
    assert len(rules) == 2
    assert rules[0]["category"] == "groceries"  # higher priority first
    conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_categorize.py -v`
Expected: FAIL

**Step 3: Implement categorize.py**

```python
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
```

**Step 4: Run tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_categorize.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/simledge/categorize.py tests/test_categorize.py
git commit -m "feat(categorize): add regex/keyword rule engine for transaction categories"
```

---

### Task 6: Analysis queries

**Files:**
- Create: `src/simledge/analysis.py`
- Create: `tests/test_analysis.py`

**Step 1: Write failing tests**

```python
# tests/test_analysis.py
from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction, snapshot_balance


def _seed_db(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_account(conn, "acct-2", "org-1", "Credit Card", "USD", "credit")

    # March transactions
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", category="groceries")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -23.99, "AMAZON", category="shopping")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-01", 4225.00, "PAYROLL", category="income")
    upsert_transaction(conn, "t4", "acct-2", "2026-03-03", -52.10, "SHELL", category="gas")

    # February transactions
    upsert_transaction(conn, "t5", "acct-1", "2026-02-15", -60.00, "WHOLE FOODS", category="groceries")
    upsert_transaction(conn, "t6", "acct-1", "2026-02-15", -30.00, "SHELL", category="gas")

    # Balances
    snapshot_balance(conn, "acct-1", "2026-03-01", 4230.50)
    snapshot_balance(conn, "acct-2", "2026-03-01", -1247.30)
    snapshot_balance(conn, "acct-1", "2026-02-01", 3800.00)
    snapshot_balance(conn, "acct-2", "2026-02-01", -1100.00)

    return conn


def test_spending_by_category(tmp_path):
    from simledge.analysis import spending_by_category
    conn = _seed_db(tmp_path)
    result = spending_by_category(conn, "2026-03")
    assert any(r["category"] == "groceries" and r["total"] == -47.32 for r in result)
    assert any(r["category"] == "gas" and r["total"] == -52.10 for r in result)
    conn.close()


def test_monthly_summary(tmp_path):
    from simledge.analysis import monthly_summary
    conn = _seed_db(tmp_path)
    result = monthly_summary(conn, "2026-03")
    assert result["total_spending"] < 0
    assert result["total_income"] > 0
    assert result["net"] == result["total_income"] + result["total_spending"]
    conn.close()


def test_net_worth(tmp_path):
    from simledge.analysis import net_worth_on_date
    conn = _seed_db(tmp_path)
    nw = net_worth_on_date(conn, "2026-03-01")
    assert nw == 4230.50 + (-1247.30)
    conn.close()


def test_spending_trend(tmp_path):
    from simledge.analysis import spending_trend
    conn = _seed_db(tmp_path)
    result = spending_trend(conn, months=2)
    assert len(result) >= 2
    # Each entry has month + total
    assert "month" in result[0]
    assert "total" in result[0]
    conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_analysis.py -v`
Expected: FAIL

**Step 3: Implement analysis.py**

```python
"""Structured analysis queries against the local database."""

from datetime import datetime, timedelta


def spending_by_category(conn, month):
    """Return spending grouped by category for a YYYY-MM month."""
    rows = conn.execute(
        "SELECT COALESCE(category, 'uncategorized') as cat, SUM(amount) as total"
        " FROM transactions"
        " WHERE strftime('%%Y-%%m', posted) = ? AND amount < 0"
        " GROUP BY cat ORDER BY total ASC",
        (month,),
    ).fetchall()
    return [{"category": r[0], "total": r[1]} for r in rows]


def monthly_summary(conn, month):
    """Return total spending, income, and net for a month."""
    row = conn.execute(
        "SELECT"
        " COALESCE(SUM(CASE WHEN amount < 0 THEN amount END), 0),"
        " COALESCE(SUM(CASE WHEN amount > 0 THEN amount END), 0)"
        " FROM transactions WHERE strftime('%%Y-%%m', posted) = ?",
        (month,),
    ).fetchone()
    spending, income = row[0], row[1]
    return {"total_spending": spending, "total_income": income, "net": income + spending}


def net_worth_on_date(conn, date):
    """Sum all account balances for a given date."""
    row = conn.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM balances WHERE date = ?",
        (date,),
    ).fetchone()
    return row[0]


def net_worth_history(conn, months=6):
    """Return net worth per month for the last N months."""
    rows = conn.execute(
        "SELECT date, SUM(balance) as total FROM balances"
        " GROUP BY date ORDER BY date DESC LIMIT ?",
        (months * 31,),  # rough upper bound on daily snapshots
    ).fetchall()
    # Deduplicate to one per month (latest date in each month)
    by_month = {}
    for date, total in rows:
        month = date[:7]
        if month not in by_month:
            by_month[month] = total
    result = [{"month": m, "net_worth": v} for m, v in sorted(by_month.items())]
    return result


def spending_trend(conn, months=6):
    """Return total spending per month for the last N months."""
    today = datetime.now()
    start = today - timedelta(days=months * 31)
    start_str = start.strftime("%Y-%m-%d")

    rows = conn.execute(
        "SELECT strftime('%%Y-%%m', posted) as month, SUM(amount) as total"
        " FROM transactions WHERE amount < 0 AND posted >= ?"
        " GROUP BY month ORDER BY month",
        (start_str,),
    ).fetchall()
    return [{"month": r[0], "total": r[1]} for r in rows]


def recent_transactions(conn, limit=20):
    """Return the most recent transactions."""
    rows = conn.execute(
        "SELECT t.id, t.posted, t.amount, t.description, t.category, t.pending,"
        " a.name as account_name"
        " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        " ORDER BY t.posted DESC, t.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {"id": r[0], "posted": r[1], "amount": r[2], "description": r[3],
         "category": r[4], "pending": bool(r[5]), "account": r[6]}
        for r in rows
    ]


def account_summary(conn):
    """Return all accounts with latest balance, grouped by institution."""
    rows = conn.execute(
        "SELECT a.id, a.name, a.type, a.currency, i.name as institution,"
        " b.balance, b.available_balance, b.date"
        " FROM accounts a"
        " LEFT JOIN institutions i ON a.institution_id = i.id"
        " LEFT JOIN balances b ON a.id = b.account_id"
        "  AND b.date = (SELECT MAX(date) FROM balances WHERE account_id = a.id)"
        " ORDER BY i.name, a.name",
    ).fetchall()
    return [
        {"id": r[0], "name": r[1], "type": r[2], "currency": r[3],
         "institution": r[4], "balance": r[5], "available_balance": r[6],
         "balance_date": r[7]}
        for r in rows
    ]
```

**Step 4: Run tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_analysis.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/simledge/analysis.py tests/test_analysis.py
git commit -m "feat(analysis): add spending, trends, net worth, and account summary queries"
```

---

### Task 7: Export for Claude Code

**Files:**
- Create: `src/simledge/export.py`
- Create: `tests/test_export.py`

**Step 1: Write failing test**

```python
# tests/test_export.py
from simledge.db import init_db, upsert_institution, upsert_account, upsert_transaction


def _seed(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    upsert_institution(conn, "org-1", "Chase", "chase.com")
    upsert_account(conn, "acct-1", "org-1", "Checking", "USD", "checking")
    upsert_transaction(conn, "t1", "acct-1", "2026-03-01", -47.32, "WHOLE FOODS", category="groceries")
    upsert_transaction(conn, "t2", "acct-1", "2026-03-02", -23.99, "AMAZON", category="shopping")
    upsert_transaction(conn, "t3", "acct-1", "2026-03-01", 4225.00, "PAYROLL", category="income")
    return conn


def test_export_markdown(tmp_path):
    from simledge.export import export_markdown
    conn = _seed(tmp_path)
    output = export_markdown(conn, "2026-03")
    assert "## SimpLedge Export" in output
    assert "WHOLE FOODS" in output
    assert "groceries" in output
    assert "| Date" in output  # table header
    conn.close()


def test_export_csv(tmp_path):
    from simledge.export import export_csv
    conn = _seed(tmp_path)
    output = export_csv(conn, "2026-03")
    lines = output.strip().split("\n")
    assert "date" in lines[0].lower()  # header row
    assert len(lines) >= 4  # header + 3 transactions
    conn.close()


def test_export_json(tmp_path):
    import json
    from simledge.export import export_json
    conn = _seed(tmp_path)
    output = export_json(conn, "2026-03")
    data = json.loads(output)
    assert "transactions" in data
    assert len(data["transactions"]) == 3
    conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_export.py -v`
Expected: FAIL

**Step 3: Implement export.py**

```python
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
        " WHERE strftime('%%Y-%%m', t.posted) = ?"
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
```

**Step 4: Run tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest tests/test_export.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/simledge/export.py tests/test_export.py
git commit -m "feat(export): add markdown, CSV, and JSON export for Claude Code analysis"
```

---

### Task 8: Wire CLI to all backends

**Files:**
- Modify: `src/simledge/cli.py`

**Step 1: Update cli.py to dispatch to real implementations**

```python
"""CLI entry point for SimpLedge."""

import argparse
import asyncio
import sys

from simledge.config import DB_PATH, CONFIG_PATH


def main():
    parser = argparse.ArgumentParser(
        prog="simledge",
        description="Personal finance TUI — sync, analyze, export",
    )
    sub = parser.add_subparsers(dest="command")

    sync_p = sub.add_parser("sync", help="fetch data from SimpleFIN")
    sync_p.add_argument("--full", action="store_true", help="re-sync all history")

    sub.add_parser("status", help="show last sync and DB stats")
    sub.add_parser("setup", help="configure SimpleFIN access")

    export_p = sub.add_parser("export", help="export data for analysis")
    export_p.add_argument("--month", help="YYYY-MM (default: current month)")
    export_p.add_argument("--format", choices=["markdown", "csv", "json"], default="markdown")

    rule_p = sub.add_parser("rule", help="manage category rules")
    rule_sub = rule_p.add_subparsers(dest="rule_command")
    add_p = rule_sub.add_parser("add", help="add a category rule")
    add_p.add_argument("pattern", help="regex or keyword to match")
    add_p.add_argument("category", help="category to assign")
    add_p.add_argument("--priority", type=int, default=0)
    rule_sub.add_parser("list", help="list all rules")
    rule_sub.add_parser("test", help="dry-run rules against uncategorized")

    args = parser.parse_args()

    if args.command is None:
        _run_tui()
    elif args.command == "sync":
        _run_sync(args)
    elif args.command == "status":
        _run_status()
    elif args.command == "setup":
        _run_setup()
    elif args.command == "export":
        _run_export(args)
    elif args.command == "rule":
        _run_rule(args)
    else:
        parser.print_help()


def _run_tui():
    print("TUI not implemented yet. Coming in Task 9+.")
    sys.exit(0)


def _run_sync(args):
    from simledge.sync import run_sync
    asyncio.run(run_sync(full=args.full))


def _run_status():
    from simledge.db import init_db, get_last_sync
    conn = init_db(DB_PATH)
    last = get_last_sync(conn)
    txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    acct_count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    print(f"Last sync: {last or 'never'}")
    print(f"Accounts: {acct_count}")
    print(f"Transactions: {txn_count}")
    print(f"Database: {DB_PATH}")
    conn.close()


def _run_setup():
    import os
    print("SimpLedge Setup")
    print("=" * 40)
    print()
    print("1. Go to https://beta-bridge.simplefin.org/ and create an account ($1.50/mo)")
    print("2. Connect your bank accounts")
    print("3. Get a setup token from the SimpleFIN dashboard")
    print()
    token = input("Paste your SimpleFIN setup token: ").strip()
    if not token:
        print("No token provided. Aborting.")
        return

    # Claim the token to get access URL
    import asyncio
    access_url = asyncio.run(_claim_token(token))
    if not access_url:
        return

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        f.write(f'[simplefin]\naccess_url = "{access_url}"\n\n[sync]\nauto_pending = true\n\n[export]\ndefault_format = "markdown"\n')
    print(f"\nConfig saved to {CONFIG_PATH}")
    print("Run 'simledge sync' to fetch your data.")


async def _claim_token(token):
    from base64 import b64decode
    import httpx

    try:
        claim_url = b64decode(token).decode("utf-8")
    except Exception:
        print("Invalid token format. Should be base64-encoded URL.")
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(claim_url, timeout=30)
            resp.raise_for_status()
            access_url = resp.text.strip()
            print("Token claimed successfully.")
            return access_url
    except httpx.HTTPError as e:
        print(f"Failed to claim token: {e}")
        return None


def _run_export(args):
    from datetime import datetime
    from simledge.db import init_db
    from simledge.export import export_markdown, export_csv, export_json

    month = args.month or datetime.now().strftime("%Y-%m")
    conn = init_db(DB_PATH)

    if args.format == "markdown":
        print(export_markdown(conn, month))
    elif args.format == "csv":
        print(export_csv(conn, month))
    elif args.format == "json":
        print(export_json(conn, month))

    conn.close()


def _run_rule(args):
    from simledge.db import init_db
    from simledge.categorize import add_rule, list_rules, apply_rules

    conn = init_db(DB_PATH)

    if args.rule_command == "add":
        add_rule(conn, args.pattern, args.category, args.priority)
        print(f"Rule added: '{args.pattern}' → {args.category}")
    elif args.rule_command == "list":
        rules = list_rules(conn)
        if not rules:
            print("No rules configured. Add one: simledge rule add 'PATTERN' category")
        else:
            print(f"{'ID':>4}  {'Priority':>8}  {'Pattern':<30}  Category")
            print("-" * 70)
            for r in rules:
                print(f"{r['id']:>4}  {r['priority']:>8}  {r['pattern']:<30}  {r['category']}")
    elif args.rule_command == "test":
        count = apply_rules(conn, dry_run=True)
        print(f"Would categorize {count} transactions.")
    else:
        print("Usage: simledge rule {add,list,test}")

    conn.close()


if __name__ == "__main__":
    main()
```

**Step 2: Reinstall and test**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && uv tool install -e . --force`
Run: `simledge --help`
Run: `simledge status`

**Step 3: Run full test suite**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest -v`
Expected: all PASS

**Step 4: Commit**

```bash
git add src/simledge/cli.py
git commit -m "feat(cli): wire all subcommands to sync, export, rule, status, setup"
```

---

### Task 9: TUI — App shell with screen switching

**Files:**
- Create: `src/simledge/tui/__init__.py`
- Create: `src/simledge/tui/app.py`
- Create: `src/simledge/tui/app.tcss`

**Step 1: Create the Textual App with mode-based screen switching**

`src/simledge/tui/__init__.py`:
```python
"""SimpLedge TUI package."""
```

`src/simledge/tui/app.py`:
```python
"""Main Textual application for SimpLedge."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Placeholder


class OverviewScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Overview — coming soon")
        yield Footer()


class TransactionsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Transactions — coming soon")
        yield Footer()


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Accounts — coming soon")
        yield Footer()


class TrendsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Trends — coming soon")
        yield Footer()


class NetWorthScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Net Worth — coming soon")
        yield Footer()


class SimpLedgeApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "SimpLedge"

    BINDINGS = [
        Binding("1", "switch_mode('overview')", "Overview", priority=True),
        Binding("2", "switch_mode('transactions')", "Transactions", priority=True),
        Binding("3", "switch_mode('accounts')", "Accounts", priority=True),
        Binding("4", "switch_mode('trends')", "Trends", priority=True),
        Binding("5", "switch_mode('networth')", "Net Worth", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    MODES = {
        "overview": OverviewScreen,
        "transactions": TransactionsScreen,
        "accounts": AccountsScreen,
        "trends": TrendsScreen,
        "networth": NetWorthScreen,
    }

    def on_mount(self):
        self.switch_mode("overview")


def run_app():
    app = SimpLedgeApp()
    app.run()
```

`src/simledge/tui/app.tcss`:
```css
Screen {
    background: $surface;
}

Placeholder {
    height: 1fr;
}
```

**Step 2: Update cli.py _run_tui()**

Replace the placeholder `_run_tui` function:

```python
def _run_tui():
    from simledge.tui.app import run_app
    run_app()
```

**Step 3: Test manually**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && uv tool install -e . --force && simledge`
Expected: TUI launches with placeholder screens, number keys switch between them, `q` quits.

**Step 4: Commit**

```bash
git add src/simledge/tui/ src/simledge/cli.py
git commit -m "feat(tui): add app shell with 5 screens and keyboard navigation"
```

---

### Task 10: TUI — Overview screen

**Files:**
- Create: `src/simledge/tui/screens/__init__.py`
- Create: `src/simledge/tui/screens/overview.py`
- Modify: `src/simledge/tui/app.py`

**Step 1: Implement overview screen**

`src/simledge/tui/screens/__init__.py`:
```python
"""TUI screen modules."""
```

`src/simledge/tui/screens/overview.py`:
```python
"""Overview screen — monthly summary, category bars, recent transactions."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from simledge.analysis import monthly_summary, spending_by_category, recent_transactions
from simledge.config import DB_PATH
from simledge.db import init_db, get_last_sync


class CategoryBar(Static):
    """A single category spending bar."""

    def __init__(self, category, amount, percentage, max_pct):
        super().__init__()
        self.category = category
        self.amount = amount
        self.percentage = percentage
        self.max_pct = max_pct

    def render(self):
        bar_width = 30
        filled = int(bar_width * (self.percentage / self.max_pct)) if self.max_pct > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        return f"  {self.category:<18} ${abs(self.amount):>9,.2f}  {bar}  {self.percentage:>5.1f}%"


class OverviewScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Label("", id="month-header")
            yield Label("", id="summary-line")
            yield Static("", id="category-section")
            yield Label("\n  Recent Transactions", id="recent-label")
            yield DataTable(id="recent-table")
            yield Label("", id="sync-status")
        yield Footer()

    def on_mount(self):
        self._refresh_data()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        month = datetime.now().strftime("%Y-%m")
        month_display = datetime.now().strftime("%B %Y")

        summary = monthly_summary(conn, month)
        categories = spending_by_category(conn, month)
        recent = recent_transactions(conn, limit=10)
        last_sync = get_last_sync(conn)
        txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        conn.close()

        # Header
        self.query_one("#month-header", Label).update(
            f"\n  {month_display}"
        )

        # Summary
        self.query_one("#summary-line", Label).update(
            f"  Spending: ${abs(summary['total_spending']):,.2f}"
            f"    Income: ${summary['total_income']:,.2f}"
            f"    Net: ${summary['net']:+,.2f}"
        )

        # Category bars
        if categories:
            total_spend = sum(abs(c["total"]) for c in categories)
            max_pct = 0
            cat_data = []
            for c in categories:
                pct = (abs(c["total"]) / total_spend * 100) if total_spend else 0
                cat_data.append((c["category"], c["total"], pct))
                max_pct = max(max_pct, pct)

            lines = ["\n  Spending by Category\n"]
            for cat, amt, pct in cat_data:
                bar_width = 30
                filled = int(bar_width * (pct / max_pct)) if max_pct > 0 else 0
                bar = "█" * filled + "░" * (bar_width - filled)
                lines.append(f"  {cat:<18} ${abs(amt):>9,.2f}  {bar}  {pct:>5.1f}%")
            self.query_one("#category-section", Static).update("\n".join(lines))

        # Recent transactions table
        table = self.query_one("#recent-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount")
        for t in recent:
            color = "[green]" if t["amount"] > 0 else "[red]"
            table.add_row(
                t["posted"],
                t["description"][:30],
                t["category"] or "—",
                f"{color}${t['amount']:+,.2f}[/]",
            )

        # Sync status
        self.query_one("#sync-status", Label).update(
            f"\n  Last sync: {last_sync or 'never'}  │  {txn_count} transactions"
        )
```

**Step 2: Update app.py to use the real OverviewScreen**

Replace the OverviewScreen import/placeholder in `app.py`:

```python
from simledge.tui.screens.overview import OverviewScreen
```

Remove the placeholder `OverviewScreen` class from `app.py`.

**Step 3: Test manually**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && uv tool install -e . --force && simledge`
Expected: Overview screen shows (with empty data if no sync yet, or with data if you've synced).

**Step 4: Commit**

```bash
git add src/simledge/tui/
git commit -m "feat(tui): implement overview screen with summary, category bars, and recent transactions"
```

---

### Task 11: TUI — Transactions screen

**Files:**
- Create: `src/simledge/tui/screens/transactions.py`
- Modify: `src/simledge/tui/app.py`

**Step 1: Implement transactions screen with search and filtering**

`src/simledge/tui/screens/transactions.py`:
```python
"""Transactions screen — searchable, filterable table."""

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, Select

from simledge.config import DB_PATH
from simledge.db import init_db


class TransactionsScreen(Screen):
    BINDINGS = [
        ("slash", "focus_search", "Search"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="filters"):
            yield Input(placeholder="Search transactions...", id="search-input")
        yield DataTable(id="txn-table")
        yield Label("", id="txn-status")
        yield Footer()

    def on_mount(self):
        self._load_transactions()

    def _load_transactions(self, search=None):
        conn = init_db(DB_PATH)

        query = (
            "SELECT t.posted, t.description, COALESCE(t.category, '—'),"
            " t.amount, a.name, t.pending"
            " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        )
        params = []

        if search:
            query += " WHERE (t.description LIKE ? OR t.category LIKE ?)"
            params = [f"%{search}%", f"%{search}%"]

        query += " ORDER BY t.posted DESC, t.id DESC LIMIT 500"

        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        conn.close()

        table = self.query_one("#txn-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount", "Account")

        for r in rows:
            posted, desc, cat, amount, acct_name, pending = r
            color = "[green]" if amount > 0 else "[red]"
            pending_mark = " ⏳" if pending else ""
            table.add_row(
                posted,
                (desc or "")[:35],
                cat,
                f"{color}${amount:+,.2f}[/]{pending_mark}",
                acct_name,
            )

        self.query_one("#txn-status", Label).update(
            f"  Showing {len(rows)} of {total} transactions"
        )

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search-input":
            search = event.value.strip()
            self._load_transactions(search=search if search else None)

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()
```

**Step 2: Update app.py**

Add import and replace placeholder:
```python
from simledge.tui.screens.transactions import TransactionsScreen
```

**Step 3: Test manually**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && uv tool install -e . --force && simledge`
Press `2` to switch to Transactions. Type in search box to filter.

**Step 4: Commit**

```bash
git add src/simledge/tui/screens/transactions.py src/simledge/tui/app.py
git commit -m "feat(tui): implement transactions screen with search and filtering"
```

---

### Task 12: TUI — Accounts screen

**Files:**
- Create: `src/simledge/tui/screens/accounts.py`
- Modify: `src/simledge/tui/app.py`

**Step 1: Implement accounts screen**

`src/simledge/tui/screens/accounts.py`:
```python
"""Accounts screen — balances grouped by institution."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="accounts-content")
        yield Footer()

    def on_mount(self):
        conn = init_db(DB_PATH)
        accounts = account_summary(conn)
        conn.close()

        if not accounts:
            self.query_one("#accounts-content", Static).update(
                "\n  No accounts yet. Run: simledge sync"
            )
            return

        # Group by institution
        groups = {}
        total_assets = 0
        total_debt = 0
        for a in accounts:
            inst = a["institution"] or "Unknown"
            groups.setdefault(inst, []).append(a)
            bal = a["balance"] or 0
            if bal >= 0:
                total_assets += bal
            else:
                total_debt += bal

        lines = ["\n"]
        for inst, accts in groups.items():
            lines.append(f"  {inst}")
            lines.append(f"  {'─' * len(inst)}")
            for a in accts:
                bal = a["balance"] or 0
                color = "[green]" if bal >= 0 else "[red]"
                lines.append(f"    {a['name']:<30} {color}${bal:>12,.2f}[/]")
            lines.append("")

        lines.append(f"  {'━' * 50}")
        lines.append(f"  Total Assets:  [green]${total_assets:>12,.2f}[/]")
        lines.append(f"  Total Debt:    [red]${total_debt:>12,.2f}[/]")
        lines.append(f"  Net Worth:     ${total_assets + total_debt:>12,.2f}")

        self.query_one("#accounts-content", Static).update("\n".join(lines))
```

**Step 2: Update app.py, test manually, commit**

```bash
git add src/simledge/tui/screens/accounts.py src/simledge/tui/app.py
git commit -m "feat(tui): implement accounts screen with balance summary by institution"
```

---

### Task 13: TUI — Trends screen

**Files:**
- Create: `src/simledge/tui/screens/trends.py`
- Modify: `src/simledge/tui/app.py`

**Step 1: Implement trends screen with plotext charts**

`src/simledge/tui/screens/trends.py`:
```python
"""Trends screen — monthly spending chart and category comparisons."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import spending_trend, spending_by_category
from simledge.config import DB_PATH
from simledge.db import init_db

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


def _render_chart(months, values):
    """Render a bar chart as a string using plotext."""
    if not HAS_PLOTEXT or not months:
        return "  No data or plotext not installed."

    plt.clear_figure()
    plt.bar(months, [abs(v) for v in values])
    plt.title("Monthly Spending")
    plt.theme("dark")
    plt.plotsize(60, 15)
    return plt.build()


class TrendsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="trends-content")
        yield Footer()

    def on_mount(self):
        conn = init_db(DB_PATH)
        trend = spending_trend(conn, months=6)

        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        prev_month_dt = now.replace(day=1)
        prev_month_dt = prev_month_dt.replace(
            month=prev_month_dt.month - 1 if prev_month_dt.month > 1 else 12,
            year=prev_month_dt.year if prev_month_dt.month > 1 else prev_month_dt.year - 1,
        )
        prev_month = prev_month_dt.strftime("%Y-%m")

        current_cats = spending_by_category(conn, current_month)
        prev_cats = spending_by_category(conn, prev_month)
        conn.close()

        lines = ["\n"]

        # Chart
        if trend:
            months = [t["month"][5:] for t in trend]  # MM only
            values = [t["total"] for t in trend]
            chart = _render_chart(months, values)
            lines.append(chart)
            lines.append("")

        # Category comparison
        if current_cats or prev_cats:
            prev_dict = {c["category"]: c["total"] for c in prev_cats}
            lines.append(f"  Category Comparison ({prev_month[5:]} → {current_month[5:]})")
            lines.append(f"  {'─' * 50}")
            for c in current_cats:
                cat = c["category"]
                cur = c["total"]
                prev = prev_dict.get(cat, 0)
                if prev != 0:
                    change = ((cur - prev) / abs(prev)) * 100
                    arrow = "▲" if change > 0 else "▼"
                    # For spending (negative values), increase means more spending
                    lines.append(
                        f"  {cat:<18} ${abs(prev):>9,.2f} → ${abs(cur):>9,.2f}  {arrow} {abs(change):.0f}%"
                    )
                else:
                    lines.append(f"  {cat:<18} {'—':>11} → ${abs(cur):>9,.2f}  new")

        if not trend and not current_cats:
            lines.append("  No data yet. Run: simledge sync")

        self.query_one("#trends-content", Static).update("\n".join(lines))
```

**Step 2: Update app.py, test manually, commit**

```bash
git add src/simledge/tui/screens/trends.py src/simledge/tui/app.py
git commit -m "feat(tui): implement trends screen with spending chart and category comparison"
```

---

### Task 14: TUI — Net Worth screen

**Files:**
- Create: `src/simledge/tui/screens/networth.py`
- Modify: `src/simledge/tui/app.py`

**Step 1: Implement net worth screen**

`src/simledge/tui/screens/networth.py`:
```python
"""Net Worth screen — net worth over time with chart."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import net_worth_history
from simledge.config import DB_PATH
from simledge.db import init_db

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


class NetWorthScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="networth-content")
        yield Footer()

    def on_mount(self):
        conn = init_db(DB_PATH)
        history = net_worth_history(conn, months=12)
        conn.close()

        lines = ["\n"]

        if not history:
            lines.append("  No balance data yet. Run: simledge sync")
            self.query_one("#networth-content", Static).update("\n".join(lines))
            return

        months = [h["month"][5:] for h in history]
        values = [h["net_worth"] for h in history]

        # Chart
        if HAS_PLOTEXT and len(history) > 1:
            plt.clear_figure()
            plt.plot(months, values, marker="braille")
            plt.title("Net Worth Over Time")
            plt.theme("dark")
            plt.plotsize(60, 15)
            lines.append(plt.build())
            lines.append("")

        # Current + change
        current = values[-1] if values else 0
        lines.append(f"  Current Net Worth: ${current:,.2f}")

        if len(values) >= 2:
            prev = values[-2]
            change = current - prev
            pct = (change / abs(prev) * 100) if prev != 0 else 0
            arrow = "▲" if change >= 0 else "▼"
            color = "[green]" if change >= 0 else "[red]"
            lines.append(
                f"  30-day Change: {color}{arrow} ${abs(change):,.2f} ({pct:+.1f}%)[/]"
            )

        self.query_one("#networth-content", Static).update("\n".join(lines))
```

**Step 2: Update app.py, test manually, commit**

```bash
git add src/simledge/tui/screens/networth.py src/simledge/tui/app.py
git commit -m "feat(tui): implement net worth screen with history chart"
```

---

### Task 15: Final app.py cleanup and integration

**Files:**
- Modify: `src/simledge/tui/app.py`

**Step 1: Replace all placeholders with real screen imports**

Final `src/simledge/tui/app.py`:

```python
"""Main Textual application for SimpLedge."""

from textual.app import App
from textual.binding import Binding

from simledge.tui.screens.overview import OverviewScreen
from simledge.tui.screens.transactions import TransactionsScreen
from simledge.tui.screens.accounts import AccountsScreen
from simledge.tui.screens.trends import TrendsScreen
from simledge.tui.screens.networth import NetWorthScreen


class SimpLedgeApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "SimpLedge"

    BINDINGS = [
        Binding("1", "switch_mode('overview')", "Overview", priority=True),
        Binding("2", "switch_mode('transactions')", "Transactions", priority=True),
        Binding("3", "switch_mode('accounts')", "Accounts", priority=True),
        Binding("4", "switch_mode('trends')", "Trends", priority=True),
        Binding("5", "switch_mode('networth')", "Net Worth", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    MODES = {
        "overview": OverviewScreen,
        "transactions": TransactionsScreen,
        "accounts": AccountsScreen,
        "trends": TrendsScreen,
        "networth": NetWorthScreen,
    }

    def on_mount(self):
        self.switch_mode("overview")


def run_app():
    app = SimpLedgeApp()
    app.run()
```

**Step 2: Run full test suite**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest -v`
Expected: all PASS

**Step 3: Manual end-to-end test**

Run: `simledge --help` — verify all commands listed
Run: `simledge status` — shows "never synced"
Run: `simledge` — TUI launches, number keys switch screens, `q` quits

**Step 4: Commit**

```bash
git add src/simledge/tui/app.py
git commit -m "refactor(tui): replace placeholder screens with real implementations"
```

---

### Task 16: Run full test suite and final verification

**Step 1: Run all tests**

Run: `cd /home/ahacad/HOME/sanctumsanctorum/simledge && pytest -v`
Expected: all tests PASS

**Step 2: Verify CLI end-to-end**

Run: `simledge --help`
Run: `simledge status`
Run: `simledge rule add "AMAZON" shopping`
Run: `simledge rule list`
Run: `simledge export --format json`

**Step 3: Verify TUI launches**

Run: `simledge`
Press 1-5, verify screens load. Press `q` to quit.

**Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```
