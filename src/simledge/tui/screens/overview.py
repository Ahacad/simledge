"""Overview screen — monthly summary, category bars, recent transactions."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from simledge.analysis import monthly_summary, spending_by_category, recent_transactions
from simledge.config import DB_PATH
from simledge.db import init_db, get_last_sync
from simledge.tui.widgets.navbar import NavBar


class OverviewScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield NavBar("overview")
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
                bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
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
                t["category"] or "\u2014",
                f"{color}${t['amount']:+,.2f}[/]",
            )

        # Sync status
        self.query_one("#sync-status", Label).update(
            f"\n  Last sync: {last_sync or 'never'}  \u2502  {txn_count} transactions"
        )
