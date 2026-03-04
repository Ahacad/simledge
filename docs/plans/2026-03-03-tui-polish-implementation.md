# TUI Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restyle the SimpLedge TUI from raw Static text dumps to lazygit-style dense bordered panels with teal accent, Sparkline charts, and consistent visual hierarchy.

**Architecture:** Pure visual refactor — same 5 screens, same data queries, same keybindings. Replace Static-with-text rendering with proper Textual containers, border_title labels, and Sparkline widgets. Drop plotext dependency.

**Tech Stack:** Textual 8.x (Sparkline, Static, DataTable, VerticalScroll, Horizontal), Rich markup for text styling.

---

### Task 1: TCSS Rewrite — Color Tokens and Panel Styles

**Files:**
- Rewrite: `src/simledge/tui/app.tcss`

**Step 1: Rewrite the full stylesheet**

```css
/* Base */
Screen {
    background: $surface;
}

/* NavBar */
NavBar {
    height: 1;
    background: #1a1a2e;
    color: $text;
    padding: 0 1;
}

/* Panels — all bordered containers use this */
.panel {
    border: round #444;
    padding: 1 2;
    margin: 0 0 1 0;
    height: auto;
}

.panel-title {
    color: #2dd4bf;
}

/* Summary numbers */
.summary-row {
    height: 3;
    padding: 1 2;
    border: round #444;
    margin: 0 0 1 0;
}

/* Transactions */
#filters {
    height: 3;
    padding: 0 1;
}

#search-input {
    width: 1fr;
}

#search-input:focus {
    border: round #2dd4bf;
}

#txn-table {
    height: 1fr;
}

#txn-status {
    height: 1;
    padding: 0 1;
    color: $text-muted;
}

/* Sparkline charts */
Sparkline {
    width: 100%;
    height: 3;
    margin: 0 0;
}

.sparkline-spending > .sparkline--max-color {
    color: #2dd4bf;
}
.sparkline-spending > .sparkline--min-color {
    color: #2dd4bf 30%;
}

.sparkline-networth > .sparkline--max-color {
    color: #22c55e;
}
.sparkline-networth > .sparkline--min-color {
    color: #22c55e 30%;
}

/* Help modal */
HelpScreen {
    align: center middle;
}

#help-box {
    width: 50;
    height: auto;
    padding: 1 2;
    border: round #2dd4bf;
    background: $surface;
}
```

**Step 2: Verify no syntax errors**

Run: `uv run python -c "from simledge.tui.app import SimpLedgeApp; print('CSS loads')"`
Expected: `CSS loads`

**Step 3: Commit**

```bash
git add src/simledge/tui/app.tcss
git commit -m "style(tui): rewrite TCSS with teal accent and panel styles"
```

---

### Task 2: NavBar — Teal Active Tab

**Files:**
- Modify: `src/simledge/tui/widgets/navbar.py`

**Step 1: Update NavBar render method**

Replace the render method with teal-colored active tabs:

```python
"""Navigation bar showing available screens."""

from textual.widgets import Static


TABS = [
    ("1", "Overview"),
    ("2", "Transactions"),
    ("3", "Accounts"),
    ("4", "Trends"),
    ("5", "Net Worth"),
]


class NavBar(Static):
    """Horizontal tab bar showing screen navigation."""

    def __init__(self, active="overview"):
        super().__init__()
        self._active = active

    def render(self):
        mode_map = {
            "overview": "1",
            "transactions": "2",
            "accounts": "3",
            "trends": "4",
            "networth": "5",
        }
        active_key = mode_map.get(self._active, "1")

        parts = []
        for key, label in TABS:
            if key == active_key:
                parts.append(f"[bold #1a1a2e on #2dd4bf] {key} {label} [/]")
            else:
                parts.append(f"[dim] {key} {label} [/]")

        return "  ".join(parts) + "  [dim]? Help  q Quit[/]"
```

**Step 2: Verify visually**

Run: `simledge` — active tab should show teal background with dark text.

**Step 3: Commit**

```bash
git add src/simledge/tui/widgets/navbar.py
git commit -m "style(tui): teal active tab in NavBar"
```

---

### Task 3: App Shell — Drop Header/Footer

**Files:**
- Modify: `src/simledge/tui/app.py`

**Step 1: Update app.py**

Remove Footer from bindings display (keep bindings themselves, just hide them from Footer). Remove Header import usage from all screens. The `show=False` on bindings hides them from the Footer.

Update `app.py` BINDINGS to use `show=False` since we use NavBar instead:

```python
BINDINGS = [
    Binding("1", "switch_mode('overview')", "Overview", priority=True, show=False),
    Binding("2", "switch_mode('transactions')", "Transactions", priority=True, show=False),
    Binding("3", "switch_mode('accounts')", "Accounts", priority=True, show=False),
    Binding("4", "switch_mode('trends')", "Trends", priority=True, show=False),
    Binding("5", "switch_mode('networth')", "Net Worth", priority=True, show=False),
    Binding("question_mark", "show_help", "? Help", priority=True, show=False),
    Binding("q", "quit", "Quit", priority=True, show=False),
]
```

**Step 2: Update all 5 screens — remove `Header()` and `Footer()` from compose()**

In each screen file (`overview.py`, `transactions.py`, `accounts.py`, `trends.py`, `networth.py`):
- Remove `yield Header()` and `yield Footer()` from `compose()`
- Remove `Header, Footer` from imports (keep only what's used)

**Step 3: Verify**

Run: `simledge` — no header bar at top, no footer bar at bottom. NavBar is the only chrome.

**Step 4: Commit**

```bash
git add src/simledge/tui/app.py src/simledge/tui/screens/*.py
git commit -m "refactor(tui): drop Header and Footer, NavBar only"
```

---

### Task 4: Overview Screen — Bordered Panels

**Files:**
- Rewrite: `src/simledge/tui/screens/overview.py`

**Step 1: Rewrite overview with bordered containers**

```python
"""Overview screen — monthly summary, category bars, recent transactions."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Static

from simledge.analysis import monthly_summary, spending_by_category, recent_transactions
from simledge.config import DB_PATH
from simledge.db import init_db, get_last_sync
from simledge.tui.widgets.navbar import NavBar


class OverviewScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("overview")
        with VerticalScroll():
            yield Vertical(Static("", id="summary-content"), id="summary-panel", classes="panel")
            yield Vertical(Static("", id="category-content"), id="category-panel", classes="panel")
            yield Vertical(DataTable(id="recent-table"), Static("", id="sync-status"), id="recent-panel", classes="panel")

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

        # Panel titles
        self.query_one("#summary-panel").border_title = month_display
        self.query_one("#category-panel").border_title = "Categories"
        recent_count = min(len(recent), 10)
        self.query_one("#recent-panel").border_title = f"Recent ({recent_count})"

        # Summary
        spending = abs(summary["total_spending"])
        income = summary["total_income"]
        net = summary["net"]
        net_color = "[#22c55e]" if net >= 0 else "[#ef4444]"
        self.query_one("#summary-content", Static).update(
            f"[bold]Spending:[/] [#ef4444]${spending:,.2f}[/]"
            f"    [bold]Income:[/] [#22c55e]${income:,.2f}[/]"
            f"    [bold]Net:[/] {net_color}${net:+,.2f}[/]"
        )

        # Category bars
        if categories:
            total_spend = sum(abs(c["total"]) for c in categories)
            max_pct = max((abs(c["total"]) / total_spend * 100) if total_spend else 0 for c in categories)

            lines = []
            for c in categories:
                cat = c["category"]
                amt = abs(c["total"])
                pct = (amt / total_spend * 100) if total_spend else 0
                bar_width = 25
                filled = int(bar_width * (pct / max_pct)) if max_pct > 0 else 0
                bar_char = "\u2588"
                empty_char = "\u2591"
                bar = f"[#2dd4bf]{bar_char * filled}[/][#333]{empty_char * (bar_width - filled)}[/]"
                lines.append(f"{cat:<18} [bold]${amt:>9,.2f}[/]  {bar}  [dim]{pct:>5.1f}%[/]")
            self.query_one("#category-content", Static).update("\n".join(lines))
        else:
            self.query_one("#category-content", Static).update("[dim]No spending data this month[/]")

        # Recent transactions
        table = self.query_one("#recent-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount")
        for t in recent:
            color = "[#22c55e]" if t["amount"] > 0 else "[#ef4444]"
            table.add_row(
                t["posted"],
                t["description"][:30],
                t["category"] or "\u2014",
                f"{color}${t['amount']:+,.2f}[/]",
            )

        # Sync status
        self.query_one("#sync-status", Static).update(
            f"[dim]Last sync: {last_sync or 'never'}  \u2502  {txn_count} transactions[/]"
        )
```

**Step 2: Verify**

Run: `simledge` — Overview should show three bordered panels with titles.

**Step 3: Commit**

```bash
git add src/simledge/tui/screens/overview.py
git commit -m "style(tui): overview screen with bordered panels"
```

---

### Task 5: Transactions Screen — Bordered Panel

**Files:**
- Rewrite: `src/simledge/tui/screens/transactions.py`

**Step 1: Rewrite with bordered container**

```python
"""Transactions screen — searchable, filterable table."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class TransactionsScreen(Screen):
    BINDINGS = [
        ("slash", "focus_search", "/ Search"),
        ("escape", "blur_search", "Esc Back"),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("transactions")
        with Vertical(id="txn-panel", classes="panel"):
            yield Input(placeholder="Press / to search...", id="search-input")
            yield DataTable(id="txn-table")
            yield Static("", id="txn-status")

    def on_mount(self):
        self.query_one("#txn-panel").border_title = "Transactions"
        self._load_transactions()
        self.query_one("#txn-table", DataTable).focus()

    def on_screen_resume(self):
        self.query_one("#txn-table", DataTable).focus()

    def _load_transactions(self, search=None):
        conn = init_db(DB_PATH)

        query = (
            "SELECT t.posted, t.description, COALESCE(t.category, '\u2014'),"
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
            color = "[#22c55e]" if amount > 0 else "[#ef4444]"
            pending_mark = " \u23f3" if pending else ""
            table.add_row(
                posted,
                (desc or "")[:35],
                cat,
                f"{color}${amount:+,.2f}[/]{pending_mark}",
                acct_name,
            )

        self.query_one("#txn-status", Static).update(
            f"[dim]Showing {len(rows)} of {total} transactions[/]"
        )

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search-input":
            search = event.value.strip()
            self._load_transactions(search=search if search else None)

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()

    def action_blur_search(self):
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.query_one("#txn-table", DataTable).focus()
        self._load_transactions()
```

**Step 2: Verify**

Run: `simledge` then press `2` — transactions inside a bordered panel, search input gets teal border on focus.

**Step 3: Commit**

```bash
git add src/simledge/tui/screens/transactions.py
git commit -m "style(tui): transactions screen with bordered panel"
```

---

### Task 6: Accounts Screen — Per-Institution Panels

**Files:**
- Rewrite: `src/simledge/tui/screens/accounts.py`

**Step 1: Rewrite with dynamic bordered panels**

```python
"""Accounts screen — balances grouped by institution."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("accounts")
        yield VerticalScroll(id="accounts-scroll")

    def on_mount(self):
        conn = init_db(DB_PATH)
        accounts = account_summary(conn)
        conn.close()

        scroll = self.query_one("#accounts-scroll", VerticalScroll)

        if not accounts:
            panel = Vertical(Static("[dim]No accounts yet. Run: simledge sync[/]"), classes="panel")
            panel.border_title = "Accounts"
            scroll.mount(panel)
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

        for inst, accts in groups.items():
            lines = []
            for a in accts:
                bal = a["balance"] or 0
                color = "#22c55e" if bal >= 0 else "#ef4444"
                lines.append(f"{a['name']:<30} [{color}]${bal:>12,.2f}[/]")
            panel = Vertical(Static("\n".join(lines)), classes="panel")
            panel.border_title = inst
            scroll.mount(panel)

        # Summary panel
        net = total_assets + total_debt
        summary_lines = [
            f"[bold]Assets:[/]   [#22c55e]${total_assets:>12,.2f}[/]",
            f"[bold]Debt:[/]     [#ef4444]${total_debt:>12,.2f}[/]",
            f"[bold]Net Worth:[/] ${net:>12,.2f}",
        ]
        summary = Vertical(Static("\n".join(summary_lines)), classes="panel")
        summary.border_title = "Summary"
        scroll.mount(summary)
```

**Step 2: Verify**

Run: `simledge` then press `3` — one bordered panel per bank, summary at bottom.

**Step 3: Commit**

```bash
git add src/simledge/tui/screens/accounts.py
git commit -m "style(tui): accounts screen with per-institution panels"
```

---

### Task 7: Trends Screen — Sparkline + Bordered Comparison

**Files:**
- Rewrite: `src/simledge/tui/screens/trends.py`

**Step 1: Rewrite with Sparkline**

```python
"""Trends screen — monthly spending sparkline and category comparisons."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Sparkline, Static

from simledge.analysis import spending_trend, spending_by_category
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class TrendsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("trends")
        with VerticalScroll():
            with Vertical(id="chart-panel", classes="panel"):
                yield Sparkline([], id="spending-sparkline", classes="sparkline-spending")
                yield Static("", id="chart-labels")
            yield Vertical(Static("", id="comparison-content"), id="comparison-panel", classes="panel")

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

        # Sparkline chart
        if trend:
            month_labels = [t["month"][5:] for t in trend]
            values = [abs(t["total"]) for t in trend]
            self.query_one("#spending-sparkline", Sparkline).data = values
            self.query_one("#chart-panel").border_title = f"Monthly Spending ({len(trend)}mo)"
            label_str = "  ".join(f"[dim]{m}[/]" for m in month_labels)
            self.query_one("#chart-labels", Static).update(label_str)
        else:
            self.query_one("#chart-panel").border_title = "Monthly Spending"
            self.query_one("#chart-labels", Static).update("[dim]No data yet[/]")

        # Category comparison
        self.query_one("#comparison-panel").border_title = f"{prev_month[5:]} \u2192 {current_month[5:]}"
        lines = []
        if current_cats or prev_cats:
            prev_dict = {c["category"]: c["total"] for c in prev_cats}
            for c in current_cats:
                cat = c["category"]
                cur = c["total"]
                prev = prev_dict.get(cat, 0)
                if prev != 0:
                    change = ((cur - prev) / abs(prev)) * 100
                    arrow = "\u25b2" if change > 0 else "\u25bc"
                    color = "#ef4444" if change > 0 else "#22c55e"
                    lines.append(
                        f"{cat:<18} [bold]${abs(prev):>9,.2f}[/] \u2192 [bold]${abs(cur):>9,.2f}[/]  [{color}]{arrow} {abs(change):.0f}%[/]"
                    )
                else:
                    lines.append(f"{cat:<18} {'':>11} \u2192 [bold]${abs(cur):>9,.2f}[/]  [dim]new[/]")

        if not lines:
            lines.append("[dim]No comparison data yet. Run: simledge sync[/]")

        self.query_one("#comparison-content", Static).update("\n".join(lines))
```

**Step 2: Verify**

Run: `simledge` then press `4` — sparkline chart in teal, comparison panel below.

**Step 3: Commit**

```bash
git add src/simledge/tui/screens/trends.py
git commit -m "style(tui): trends screen with Sparkline, drop plotext"
```

---

### Task 8: Net Worth Screen — Sparkline + Summary Panel

**Files:**
- Rewrite: `src/simledge/tui/screens/networth.py`

**Step 1: Rewrite with Sparkline**

```python
"""Net Worth screen — net worth over time with sparkline chart."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Sparkline, Static

from simledge.analysis import net_worth_history
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class NetWorthScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("networth")
        with VerticalScroll():
            with Vertical(id="nw-chart-panel", classes="panel"):
                yield Sparkline([], id="nw-sparkline", classes="sparkline-networth")
                yield Static("", id="nw-chart-labels")
            yield Vertical(Static("", id="nw-summary"), id="nw-summary-panel", classes="panel")

    def on_mount(self):
        conn = init_db(DB_PATH)
        history = net_worth_history(conn, months=12)
        conn.close()

        chart_panel = self.query_one("#nw-chart-panel")
        summary_panel = self.query_one("#nw-summary-panel")

        if not history:
            chart_panel.border_title = "Net Worth"
            self.query_one("#nw-chart-labels", Static).update("[dim]No balance data yet. Run: simledge sync[/]")
            summary_panel.border_title = "Current"
            self.query_one("#nw-summary", Static).update("[dim]No data[/]")
            return

        month_labels = [h["month"][5:] for h in history]
        values = [h["net_worth"] for h in history]

        # Sparkline
        self.query_one("#nw-sparkline", Sparkline).data = values
        chart_panel.border_title = f"Net Worth ({len(history)}mo)"
        label_str = "  ".join(f"[dim]{m}[/]" for m in month_labels)
        self.query_one("#nw-chart-labels", Static).update(label_str)

        # Summary
        summary_panel.border_title = "Current"
        current = values[-1] if values else 0
        lines = [f"[bold]Net Worth:[/] ${current:,.2f}"]

        if len(values) >= 2:
            prev = values[-2]
            change = current - prev
            pct = (change / abs(prev) * 100) if prev != 0 else 0
            arrow = "\u25b2" if change >= 0 else "\u25bc"
            color = "#22c55e" if change >= 0 else "#ef4444"
            lines.append(
                f"[bold]30-day Change:[/] [{color}]{arrow} ${abs(change):,.2f} ({pct:+.1f}%)[/]"
            )

        self.query_one("#nw-summary", Static).update("\n".join(lines))
```

**Step 2: Verify**

Run: `simledge` then press `5` — green sparkline, bordered summary panel.

**Step 3: Commit**

```bash
git add src/simledge/tui/screens/networth.py
git commit -m "style(tui): net worth screen with Sparkline, drop plotext"
```

---

### Task 9: Remove plotext Dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Remove plotext from dependencies**

In `pyproject.toml`, change:
```
dependencies = [
    "textual>=1.0",
    "httpx>=0.27",
    "plotext>=5.3",
]
```

To:
```
dependencies = [
    "textual>=1.0",
    "httpx>=0.27",
]
```

**Step 2: Run tests**

Run: `uv run pytest -x`
Expected: 22 passed

**Step 3: Reinstall and verify**

Run: `uv tool install -e . --force && simledge`
Expected: TUI launches, all 5 screens render correctly.

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: remove plotext dependency (replaced by Sparkline)"
```

---

### Task 10: Final Visual QA Pass

**Step 1: Test all screens**

Run `simledge` and check:
- Tab 1 (Overview): Three bordered panels, teal category bars, green/red amounts
- Tab 2 (Transactions): Search input teal on focus, table fills panel
- Tab 3 (Accounts): Per-institution panels, summary at bottom
- Tab 4 (Trends): Teal sparkline, month labels, comparison panel
- Tab 5 (Net Worth): Green sparkline, summary with change indicator
- `?` opens help modal
- `q` quits
- All keybindings 1-5 work

**Step 2: Fix any visual issues found during QA**

Adjust padding, spacing, border colors as needed.

**Step 3: Run full test suite**

Run: `uv run pytest -x`
Expected: 22 passed

**Step 4: Final commit**

```bash
git add -A
git commit -m "style(tui): visual QA fixes"
```
