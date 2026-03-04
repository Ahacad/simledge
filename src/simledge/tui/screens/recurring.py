"""Bills screen — recurring transaction detection and display."""

from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Static

from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.recurring import detect_recurring
from simledge.tui.widgets.navbar import NavBar


class RecurringScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("recurring")
        with VerticalScroll(id="recurring-scroll"):
            with Vertical(id="bills-panel", classes="panel"):
                yield DataTable(id="bills-table")
            with Vertical(id="bills-summary", classes="panel"):
                yield Static("", id="bills-summary-text")

    def on_mount(self):
        self.query_one("#bills-panel").border_title = "Bills & Subscriptions"
        self.query_one("#bills-summary").border_title = "Summary"
        self._load_recurring()
        self.query_one("#bills-table", DataTable).focus()

    def on_screen_resume(self):
        self.query_one("#bills-table", DataTable).focus()

    def _load_recurring(self):
        conn = init_db(DB_PATH)
        items = detect_recurring(conn)
        conn.close()

        table = self.query_one("#bills-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "Description", "Amount", "Frequency", "Last", "Next Expected",
            "Account",
        )

        today = datetime.now().date()
        soon = today + timedelta(days=7)
        monthly_total = 0.0
        count = 0

        for item in items:
            amt = item["last_amount"]
            amt_str = f"[#ef4444]${abs(amt):,.2f}[/]"

            try:
                next_dt = datetime.strptime(item["next_expected"], "%Y-%m-%d").date()
                if next_dt <= soon:
                    next_str = f"[yellow]{item['next_expected']}[/]"
                else:
                    next_str = item["next_expected"]
            except (ValueError, TypeError):
                next_str = item["next_expected"]

            freq = item["frequency"].capitalize()

            table.add_row(
                (item["description"] or "")[:30],
                amt_str,
                freq,
                item["last_date"],
                next_str,
                item["account"],
            )
            count += 1

            # Accumulate monthly equivalent
            monthly_amt = abs(amt)
            if item["frequency"] == "weekly":
                monthly_amt *= 4.33
            elif item["frequency"] == "yearly":
                monthly_amt /= 12
            monthly_total += monthly_amt

        annual_total = monthly_total * 12
        summary_lines = [
            f"[bold]Monthly recurring:[/]  [#ef4444]${monthly_total:>10,.2f}[/]",
            f"[bold]Annual recurring:[/]   [#ef4444]${annual_total:>10,.2f}[/]",
            f"[bold]{count}[/] bills & subscriptions detected",
        ]
        self.query_one("#bills-summary-text", Static).update(
            "\n".join(summary_lines)
        )
