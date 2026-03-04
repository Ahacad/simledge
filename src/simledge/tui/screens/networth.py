"""Net Worth screen — net worth over time with sparkline chart."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Sparkline, Static

from simledge.analysis import net_worth_history
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class NetWorthScreen(Screen):
    BINDINGS = [
        Binding("minus", "decrease_lookback", "- Range", show=False),
        Binding("plus,equals", "increase_lookback", "+ Range", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("networth")
        with VerticalScroll():
            with Vertical(id="nw-chart-panel", classes="panel"):
                yield Sparkline([], id="nw-sparkline", classes="sparkline-networth")
                yield Static("", id="nw-chart-labels")
            yield Vertical(Static("", id="nw-summary"), id="nw-summary-panel", classes="panel")

    def on_mount(self):
        self._lookback = 12
        self._refresh_data()

    def action_decrease_lookback(self):
        if self._lookback > 3:
            self._lookback -= 1
            self._refresh_data()

    def action_increase_lookback(self):
        if self._lookback < 60:
            self._lookback += 1
            self._refresh_data()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        account_ids = self.app.active_account_ids
        history = net_worth_history(conn, months=self._lookback, account_ids=account_ids)
        conn.close()

        chart_panel = self.query_one("#nw-chart-panel")
        summary_panel = self.query_one("#nw-summary-panel")

        if not history:
            chart_panel.border_title = f"Net Worth ({self._lookback}mo)"
            self.query_one("#nw-chart-labels", Static).update("[dim]No balance data yet. Run: simledge sync[/]")
            summary_panel.border_title = "Current"
            self.query_one("#nw-summary", Static).update("[dim]No data[/]")
            return

        month_labels = [h["month"][5:] for h in history]
        values = [h["net_worth"] for h in history]

        # Sparkline
        self.query_one("#nw-sparkline", Sparkline).data = values
        chart_panel.border_title = f"Net Worth ({self._lookback}mo)"
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
            arrow = "▲" if change >= 0 else "▼"
            color = "#22c55e" if change >= 0 else "#ef4444"
            lines.append(
                f"[bold]30-day Change:[/] [{color}]{arrow} ${abs(change):,.2f} ({pct:+.1f}%)[/]"
            )

        self.query_one("#nw-summary", Static).update("\n".join(lines))
