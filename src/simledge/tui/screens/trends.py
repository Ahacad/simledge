"""Trends screen — monthly spending sparkline and category comparisons."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Sparkline, Static

from simledge.analysis import spending_trend, spending_by_category
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class TrendsScreen(Screen):
    BINDINGS = [
        Binding("minus", "decrease_lookback", "- Range", show=False),
        Binding("plus,equals", "increase_lookback", "+ Range", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("trends")
        with VerticalScroll():
            with Vertical(id="chart-panel", classes="panel"):
                yield Sparkline([], id="spending-sparkline", classes="sparkline-spending")
                yield Static("", id="chart-labels")
            yield Vertical(Static("", id="comparison-content"), id="comparison-panel", classes="panel")

    def on_mount(self):
        self._lookback = 6
        self._refresh_data()

    def action_decrease_lookback(self):
        if self._lookback > 3:
            self._lookback -= 1
            self._refresh_data()

    def action_increase_lookback(self):
        if self._lookback < 24:
            self._lookback += 1
            self._refresh_data()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        account_ids = self.app.active_account_ids
        trend = spending_trend(conn, months=self._lookback, account_ids=account_ids)

        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        prev_month_dt = now.replace(day=1)
        prev_month_dt = prev_month_dt.replace(
            month=prev_month_dt.month - 1 if prev_month_dt.month > 1 else 12,
            year=prev_month_dt.year if prev_month_dt.month > 1 else prev_month_dt.year - 1,
        )
        prev_month = prev_month_dt.strftime("%Y-%m")

        current_cats = spending_by_category(conn, current_month, account_ids=account_ids)
        prev_cats = spending_by_category(conn, prev_month, account_ids=account_ids)
        conn.close()

        # Sparkline chart
        if trend:
            month_labels = [t["month"][5:] for t in trend]
            values = [abs(t["total"]) for t in trend]
            self.query_one("#spending-sparkline", Sparkline).data = values
            self.query_one("#chart-panel").border_title = f"Monthly Spending ({self._lookback}mo)"
            label_str = "  ".join(f"[dim]{m}[/]" for m in month_labels)
            self.query_one("#chart-labels", Static).update(label_str)
        else:
            self.query_one("#chart-panel").border_title = f"Monthly Spending ({self._lookback}mo)"
            self.query_one("#chart-labels", Static).update("[dim]No data yet[/]")

        # Category comparison
        self.query_one("#comparison-panel").border_title = f"{prev_month[5:]} → {current_month[5:]}"
        lines = []
        if current_cats or prev_cats:
            prev_dict = {c["category"]: c["total"] for c in prev_cats}
            for c in current_cats:
                cat = c["category"]
                cur = c["total"]
                prev = prev_dict.get(cat, 0)
                if prev != 0:
                    change = ((cur - prev) / abs(prev)) * 100
                    arrow = "▲" if change > 0 else "▼"
                    color = "#ef4444" if change > 0 else "#22c55e"
                    lines.append(
                        f"{cat:<18} [bold]${abs(prev):>9,.2f}[/] → [bold]${abs(cur):>9,.2f}[/]  [{color}]{arrow} {abs(change):.0f}%[/]"
                    )
                else:
                    lines.append(f"{cat:<18} {'':>11} → [bold]${abs(cur):>9,.2f}[/]  [dim]new[/]")

        if not lines:
            lines.append("[dim]No comparison data yet. Run: simledge sync[/]")

        self.query_one("#comparison-content", Static).update("\n".join(lines))
