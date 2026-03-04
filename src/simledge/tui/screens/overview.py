"""Overview screen — monthly summary, category bars, recent transactions."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Static

from simledge.analysis import monthly_summary, spending_by_category_grouped, recent_transactions, income_by_category
from simledge.config import DB_PATH
from simledge.db import init_db, get_last_sync
from simledge.tui.widgets.navbar import NavBar


class OverviewScreen(Screen):
    BINDINGS = [
        Binding("h", "prev_month", "Prev month", show=False),
        Binding("left", "prev_month", "Prev month", show=False),
        Binding("l", "next_month", "Next month", show=False),
        Binding("right", "next_month", "Next month", show=False),
        Binding("t", "goto_today", "Today", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("overview")
        with VerticalScroll():
            yield Vertical(Static("", id="summary-content"), id="summary-panel", classes="panel")
            yield Vertical(Static("", id="category-content"), id="category-panel", classes="panel")
            yield Vertical(DataTable(id="recent-table"), Static("", id="sync-status"), id="recent-panel", classes="panel")

    def on_mount(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._refresh_data()

    def action_prev_month(self):
        y, m = int(self._month[:4]), int(self._month[5:])
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        self._month = f"{y:04d}-{m:02d}"
        self._refresh_data()

    def action_next_month(self):
        now = datetime.now().strftime("%Y-%m")
        if self._month >= now:
            return
        y, m = int(self._month[:4]), int(self._month[5:])
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        new_month = f"{y:04d}-{m:02d}"
        if new_month > now:
            return
        self._month = new_month
        self._refresh_data()

    def action_goto_today(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._refresh_data()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        month = self._month
        month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")

        account_ids = self.app.active_account_ids
        summary = monthly_summary(conn, month, account_ids=account_ids)
        categories = spending_by_category_grouped(conn, month, account_ids=account_ids)
        inc_cats = income_by_category(conn, month, account_ids=account_ids)
        recent = recent_transactions(conn, limit=10, account_ids=account_ids)
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
        income_detail = ""
        if len(inc_cats) > 1:
            top_sources = " \u00b7 ".join(
                f"{c['category']} ${c['total']:,.0f}" for c in inc_cats[:3]
            )
            income_detail = f"\n[dim]  ({top_sources})[/]"
        self.query_one("#summary-content", Static).update(
            f"[bold]Spending:[/] [#ef4444]${spending:,.2f}[/]"
            f"    [bold]Income:[/] [#22c55e]${income:,.2f}[/]"
            f"    [bold]Net:[/] {net_color}${net:+,.2f}[/]"
            + income_detail
        )

        # Category bars (hierarchical)
        if categories:
            total_spend = sum(abs(c["total"]) for c in categories)
            max_pct = max((abs(c["total"]) / total_spend * 100) if total_spend else 0 for c in categories)
            bar_width = 25
            bar_char = "\u2588"
            empty_char = "\u2591"

            lines = []
            for c in categories:
                cat = c["category"]
                amt = abs(c["total"])
                pct = (amt / total_spend * 100) if total_spend else 0
                filled = int(bar_width * (pct / max_pct)) if max_pct > 0 else 0
                bar = f"[#2dd4bf]{bar_char * filled}[/][#333]{empty_char * (bar_width - filled)}[/]"
                lines.append(f"{cat:<18} [bold]${amt:>9,.2f}[/]  {bar}  [dim]{pct:>5.1f}%[/]")
                for child in c.get("children", []):
                    child_name = child["category"].split(":", 1)[1]
                    child_amt = abs(child["total"])
                    child_pct = (child_amt / total_spend * 100) if total_spend else 0
                    child_filled = int(bar_width * (child_pct / max_pct)) if max_pct > 0 else 0
                    child_bar = f"[#1a9985]{bar_char * child_filled}[/][#333]{empty_char * (bar_width - child_filled)}[/]"
                    lines.append(f"  {child_name:<16} [bold]${child_amt:>9,.2f}[/]  {child_bar}  [dim]{child_pct:>5.1f}%[/]")
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
