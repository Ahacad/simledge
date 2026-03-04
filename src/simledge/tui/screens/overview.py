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
