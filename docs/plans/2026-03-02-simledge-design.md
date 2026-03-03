# SimpLedge — Design Document

**Date:** 2026-03-02
**Status:** Approved

## What

Personal finance data tool. Syncs bank/card/investment data via SimpleFIN, stores locally in SQLite, provides structured analysis through a TUI dashboard. AI analysis via external Claude Code, not embedded.

## Why

Quicken Simplifi has no API. SimpleFIN ($1.50/mo) provides read-only bank data access. Build a tool that owns the data locally, provides better analysis, and is Claude Code-friendly for ad-hoc AI queries.

## Architecture

Monolith CLI+TUI. Single Python package, one entry point (`simledge`), subcommands for sync/export/rules, TUI as the default/primary interface.

```
SimpleFIN API ($1.50/mo)
    ↓ GET /accounts (daily, ≤24 req/day)
simledge sync
    ↓ normalize, categorize, upsert
SQLite (~/.local/share/simledge/simledge.db)
    ↓ structured queries
simledge TUI (Textual)
    ↓ or
simledge export → Claude Code (external AI analysis)
```

## Tech Stack

- Python 3.11+, `uv` package manager, hatchling build
- `textual` — TUI framework
- `httpx` — async HTTP client for SimpleFIN
- `plotext` — terminal charts
- SQLite — built-in, single file storage
- Config: TOML (`~/.config/simledge/config.toml`)

## Project Structure

```
simledge/
├── src/simledge/
│   ├── __init__.py
│   ├── cli.py          # argparse dispatcher
│   ├── config.py       # constants, paths, credential location
│   ├── compat.py       # platform detection, XDG dirs
│   ├── db.py           # schema, migrations, query helpers
│   ├── sync.py         # SimpleFIN client, normalization, DB insert
│   ├── categorize.py   # rule engine: regex/keyword → category
│   ├── analysis.py     # structured queries: spending, trends, net worth
│   ├── export.py       # dump as markdown/CSV/JSON for Claude Code
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py      # Textual App, screen routing
│   │   ├── screens/    # one file per dashboard screen
│   │   └── widgets/    # reusable chart/table widgets
│   └── log.py          # logging setup
├── tests/
├── docs/plans/
├── pyproject.toml
└── CLAUDE.md
```

## Data Model (SQLite, v0)

Schema will be refined after seeing real SimpleFIN data.

```sql
CREATE TABLE institutions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT
);

CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    institution_id TEXT REFERENCES institutions(id),
    name TEXT NOT NULL,
    currency TEXT DEFAULT 'USD',
    type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE balances (
    account_id TEXT REFERENCES accounts(id),
    date TEXT NOT NULL,
    balance REAL NOT NULL,
    available_balance REAL,
    PRIMARY KEY (account_id, date)
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT REFERENCES accounts(id),
    posted TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    category TEXT,
    pending INTEGER DEFAULT 0,
    raw_json TEXT
);

CREATE TABLE category_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    category TEXT NOT NULL,
    priority INTEGER DEFAULT 0
);

CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at TEXT DEFAULT (datetime('now')),
    accounts_updated INTEGER,
    transactions_added INTEGER,
    status TEXT
);
```

Key decisions:
- Balance snapshots daily → net worth history over time
- Category rules in DB, not config file
- `raw_json` per transaction for debugging
- SimpleFIN transaction ID as primary key → natural dedup

## CLI Commands

```bash
simledge                               # launch TUI (default)
simledge sync                          # fetch from SimpleFIN
simledge sync --full                   # re-sync all history
simledge export                        # last 30 days as markdown
simledge export --month 2026-03        # specific month
simledge export --format csv|json      # other formats
simledge rule add "AMAZON" shopping    # add category rule
simledge rule list                     # show all rules
simledge rule test                     # dry-run against uncategorized
simledge status                        # last sync, DB stats
simledge setup                         # first-run wizard
```

## Sync Flow

1. Read SimpleFIN access URL from config
2. `GET {access_url}/accounts?start-date={last_sync}&pending=1`
3. Upsert institutions, accounts
4. Snapshot today's balances
5. Upsert transactions (dedup by ID)
6. Run category rules on uncategorized
7. Log sync result
8. Print summary

## TUI Design

Five screens, tab/number-key navigation, keyboard-driven, vim-style.

### Overview (default)
- Month summary: total spending, income, net
- Category breakdown with horizontal bars and percentages
- Recent transactions list
- Sync status footer

### Transactions
- Searchable, filterable table
- Filter by: account, category, date range
- Drill-down: enter on row → detail panel
- Inline category assignment (`c` key)

### Accounts
- Grouped by institution
- Balance per account
- Total assets, total debt, net worth

### Trends
- Monthly spending chart (plotext sparklines/bars)
- Category month-over-month comparison
- 6-month rolling view

### Net Worth
- Net worth over time chart
- 30-day change with percentage

### Interactivity
- Drill-down everywhere: category → its transactions, account → its transactions
- Global date range filter across all screens
- Modal detail panels (side panel or popup)
- Responsive: Textual CSS handles terminal resize
- Color: expenses red, income green, neutral white

## Export for AI

```bash
simledge export --month 2026-03 | claude "analyze my spending"
```

Markdown format: summary table + category breakdown + full transaction table. Token-efficient, human-readable.

## Config

`~/.config/simledge/config.toml`:

```toml
[simplefin]
access_url = "https://bridge.simplefin.org/simplefin/accounts/..."

[sync]
auto_pending = true

[export]
default_format = "markdown"
```

## Error Handling

- SimpleFIN down → sync logs error, TUI shows stale warning
- Duplicate transactions → upsert by ID, idempotent
- Uncategorized → shown as "uncategorized" in grey, filterable
- First run → `simledge setup` wizard
- No data → empty state with instructions

## Non-Goals (v1)

- Embedded AI (no Claude API calls from the app)
- Web UI
- Multi-user
- Budget planning / goal setting (future)
- Transaction editing / manual entry (future)
