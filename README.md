# SimpLedge

Personal finance TUI — sync bank data via [SimpleFIN](https://www.simplefin.org/), store locally in SQLite, analyze through interactive dashboards.

[![CI](https://github.com/Ahacad/simledge/actions/workflows/ci.yml/badge.svg)](https://github.com/Ahacad/simledge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg)](https://www.python.org/downloads/)

<!-- screenshot placeholder -->

## Features

- **SimpleFIN sync** — pull transactions, balances, and accounts from 12,000+ banks via SimpleFIN Bridge
- **10 dashboard screens** — Overview, Transactions, Accounts, Trends, Net Worth, Rules, Bills, Budget, Goals, Watchlists
- **Category rules** — regex/keyword engine to auto-categorize transactions, with dry-run testing
- **Budget tracking** — set monthly limits per category, see actual vs. budget with progress bars
- **Savings goals** — track progress toward targets linked to specific accounts
- **Spending watchlists** — named trackers with monthly targets filtered by category, tag, or description
- **Recurring bill detection** — auto-detect bills with list and calendar views
- **Net worth history** — track total net worth over time with charts
- **Spending & income trends** — monthly charts, year-over-year and year-to-date comparisons
- **Transaction search & filters** — quick search (`/`), advanced filters by category/account/amount/date
- **Privacy mode** — toggle (`p`) to mask all dollar amounts on screen
- **Data export** — markdown, CSV, or JSON for external analysis (e.g. pipe to Claude)
- **Account filtering** — show/hide accounts across all screens
- **Auto-sync** — syncs automatically when last sync was >24h ago
- **Vim-style navigation** — `h/l` for months, `j/k` for lists, number keys for screens
- **Local-only storage** — all data stays in a local SQLite database, no cloud

## Install

```bash
# Primary (requires uv)
uv tool install git+https://github.com/Ahacad/simledge.git

# Alternative (pipx)
pipx install git+https://github.com/Ahacad/simledge.git
```

## Quick Start

```bash
# 1. Configure SimpleFIN (creates ~/.config/simledge/config.toml)
simledge setup

# 2. Fetch your bank data
simledge sync

# 3. Launch the TUI
simledge
```

## Keybindings

### Navigation

| Key | Action |
|-----|--------|
| `1`–`0` | Switch screens: Overview, Transactions, Accounts, Trends, Net Worth, Rules, Bills, Budget, Goals, Watchlists |
| `h` / `←` | Previous month |
| `l` / `→` | Next month |
| `t` | Jump to today |
| `-` / `+` | Adjust date range |

### Actions

| Key | Action |
|-----|--------|
| `s` | Sync from SimpleFIN |
| `a` | Filter accounts |
| `p` | Toggle privacy mode |
| `/` | Quick search (Transactions) |
| `f` | Advanced filters (Transactions) |
| `?` | Show help |
| `Esc` | Clear filters / close modal |
| `q` | Quit |

### CRUD (Rules, Budget, Goals, Watchlists)

| Key | Action |
|-----|--------|
| `n` | New item |
| `d` | Delete item |
| `Enter` | Edit item |
| `j` / `↓` | Next item |
| `k` / `↑` | Previous item |

### Bills

| Key | Action |
|-----|--------|
| `v` | Toggle list/calendar view |

## CLI Reference

```
simledge                          Launch TUI
simledge setup                    Configure SimpleFIN access
simledge sync                     Fetch data from SimpleFIN
simledge sync --full              Re-sync all history
simledge sync --start YYYY-MM-DD  Fetch from a specific date
simledge sync --raw               Dump raw SimpleFIN JSON
simledge status                   Show last sync time and DB stats
simledge export                   Export current month (markdown)
simledge export --month YYYY-MM   Export a specific month
simledge export --format csv      Export as CSV
simledge export --format json     Export as JSON
simledge rule add PATTERN CAT     Add a category rule
simledge rule list                List all rules
simledge rule test                Dry-run rules against uncategorized
```

## Development

```bash
git clone https://github.com/Ahacad/simledge.git
cd simledge
uv sync --group dev
uv tool install -e .

# Run tests
pytest

# Lint
ruff check src/
ruff format --check src/
```

## License

[MIT](LICENSE)
