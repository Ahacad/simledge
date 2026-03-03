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

## DATA SAFETY — READ THIS FIRST

This app handles real bank credentials and financial data. Treat every piece of user data as radioactive.

- **NEVER commit, log, print, or expose**: SimpleFIN access URLs, account numbers, balances, transaction amounts, descriptions, or any PII
- **NEVER include real financial data** in test fixtures, examples, error messages, or commit messages
- **NEVER read or output** `~/.config/simledge/config.toml` or `~/.local/share/simledge/simledge.db` — these contain secrets and real financial data
- **Config file** (`config.toml`) contains the SimpleFIN access URL which is effectively a bearer token to all linked bank accounts. Guard it like a password.
- **DB file** (`simledge.db`) contains full transaction history, balances, and account names. Never reference its contents.
- **Export files** contain raw financial data. Never read, display, or commit them.
- **In code**: sanitize log messages, never log transaction details or balances at INFO level or above, never include real amounts in error messages
- **In tests**: always use obviously fake data (amounts like 100.00, descriptions like "TEST_MERCHANT")

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
