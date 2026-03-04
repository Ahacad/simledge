# TUI Polish Design — Dense Panels Style

## Visual Direction

lazygit-inspired: dense bordered panels, information-packed, dark + teal accent.

## Global Changes

- **Drop Header and Footer** — NavBar is the only chrome. Saves 2 lines.
- **Every section gets a bordered container** with `border_title` — no more raw Static text dumps.
- **Border style**: `round`, dim color by default.
- **Drop plotext** — replace with Textual-native Sparkline and Rich horizontal bars.
- **Color tokens**: teal accent, green for income/gains, red for spending/losses.

## NavBar

- 1 line, top of every screen.
- Active tab: teal background. Inactive: dim text.
- Shows `? Help  q Quit` at the right.

## Screen 1: Overview

Three bordered panels stacked:

```
[Monthly Summary]  border_title="March 2026"
  Spending: $X,XXX.XX    Income: $X,XXX.XX    Net: +$X,XXX.XX

[Spending by Category]  border_title="Categories"
  Groceries      $1,234.56  ████████████░░░░░░  45.2%
  Dining         $  567.89  ██████░░░░░░░░░░░░  20.8%
  ...

[Recent Transactions]  border_title="Recent (10)"
  DataTable: Date | Description | Category | Amount
```

## Screen 2: Transactions

```
[Search + Table]  border_title="Transactions"
  [/ search input]
  DataTable: Date | Description | Category | Amount | Account
  Status line: Showing X of Y
```

Search input: teal border when focused.

## Screen 3: Accounts

One bordered panel per institution:

```
[Chase]  border_title="Chase"
  Checking              $12,345.67
  Savings                $5,432.10

[Schwab]  border_title="Charles Schwab"
  Brokerage            $45,678.90

[Totals]  border_title="Summary"
  Assets:   $XX,XXX.XX
  Debt:     -$X,XXX.XX
  Net:      $XX,XXX.XX
```

## Screen 4: Trends

```
[Sparkline]  border_title="Monthly Spending (6mo)"
  Sparkline widget, full width, teal color

[Category Comparison]  border_title="02 -> 03"
  Category       Feb          Mar         Change
  Groceries      $1,234.56 -> $1,100.00   ▼ 11%
```

## Screen 5: Net Worth

```
[Sparkline]  border_title="Net Worth (12mo)"
  Sparkline widget, full width, green color

[Summary]  border_title="Current"
  Net Worth: $64,483.20
  30-day Change: ▲ $2,435.65 (+3.9%)
```

## Files Changed

- `app.py` — remove Header/Footer from compose, keep HelpScreen
- `app.tcss` — full rewrite: color tokens, panel styles, sparkline colors
- `widgets/navbar.py` — teal active tab styling
- `screens/overview.py` — wrap sections in bordered containers
- `screens/transactions.py` — wrap in bordered container
- `screens/accounts.py` — one container per institution + summary container
- `screens/trends.py` — Sparkline + bordered comparison panel, drop plotext
- `screens/networth.py` — Sparkline + bordered summary panel, drop plotext

## Dependencies

- plotext can be removed from pyproject.toml (replaced by Sparkline)
