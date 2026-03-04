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
- textual (TUI), httpx (HTTP)
- SQLite (stdlib), tomllib (stdlib)
- pytest for testing

## Commands

```bash
uv tool install -e .           # install (dev)
uv tool install -e . --force   # update after changes
pytest                         # run tests
uv run ruff check src/ tests/  # lint
uv run ruff format src/ tests/ # format
simledge                       # launch TUI
simledge sync                  # fetch from SimpleFIN
simledge export                # export for AI analysis
./scripts/release.sh patch     # bump 0.1.0 → 0.1.1, commit, tag
./scripts/release.sh minor     # bump 0.1.0 → 0.2.0, commit, tag
./scripts/release.sh major     # bump 0.1.0 → 1.0.0, commit, tag
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

## TUI Visual Style

lazygit-inspired dense panels. Do NOT deviate from this style.

- **Dark + teal accent** (`#2dd4bf`). Green `#22c55e` for income/gains, red `#ef4444` for spending/losses.
- **Every section in a bordered panel** — `Vertical(classes="panel")` with `border_title`. No raw Static text dumps.
- **No Header or Footer** — NavBar is the only chrome (1 line, top). Active tab: dark text on teal background.
- **Charts use Textual Sparkline** — not plotext. Sparkline colors set via TCSS component classes.
- **Borders**: `round #444` style. Help modal uses `round #2dd4bf`.
- **Dynamic panels** (e.g. Accounts per-institution) mounted at runtime via `scroll.mount(panel)`.
- **All styling in `app.tcss`** — screens define structure, TCSS defines appearance.

## Releasing

Use `./scripts/release.sh <patch|minor|major>`. It bumps the version in `pyproject.toml`, commits, and creates a git tag. Then push with `git push origin master --tags` — the GitHub Action builds and publishes the release.

## Commits and Docs

- **NEVER commit `docs/` directory** — design docs and plans are local working notes, not shipped artifacts
- Auto-commit after each logical chunk
- Conventional Commits: `type(scope): description`
- Run `pytest` and `ruff check` before committing

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

## Development Workflow — Team Mode

For non-trivial features, use the team leader + parallel teammates pattern:

1. **Team leader discusses with human** — clarify requirements, specs, edge cases, and scope before any code is written. Agree on the plan.
2. **Team leader creates tasks** — break the plan into independent, parallelizable units of work.
3. **Spawn teammates in worktrees** — each teammate works in an isolated git worktree (`isolation: "worktree"`), so they can't step on each other. Assign one task (or a small group of related tasks) per teammate.
4. **Teammates work in parallel** — each builds, tests, and commits in their own worktree branch. Follow all project conventions (code style, testing, commit messages).
5. **Merge and report** — team leader merges each teammate's branch into the main working branch, resolves any conflicts, runs full test suite, and reports results to the human.

Key rules:
- **Worktree isolation is mandatory** for parallel teammates — never have two agents editing the same branch.
- **Each teammate runs `pytest` before finishing** — don't hand broken code back to the leader.
- **Team leader owns the merge** — teammates do not push to master or merge themselves.
- **Keep the human in the loop** — report progress at milestones, surface blockers immediately.

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
