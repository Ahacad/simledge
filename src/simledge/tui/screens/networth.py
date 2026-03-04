"""Net Worth screen — net worth over time with plotext chart."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import net_worth_history
from simledge.cashflow import project_balances
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.charts import render_line_chart, GREEN, TEAL
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
                yield Static("", id="nw-chart")
            yield Vertical(Static("", id="nw-summary"), id="nw-summary-panel", classes="panel")
            with Vertical(id="cf-panel", classes="panel"):
                yield Static("", id="cf-chart")
                yield Static("", id="cf-summary")
                yield Static("", id="cf-warnings")

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

        chart_panel = self.query_one("#nw-chart-panel")
        summary_panel = self.query_one("#nw-summary-panel")

        if not history:
            chart_panel.border_title = f"Net Worth ({self._lookback}mo)"
            self.query_one("#nw-chart", Static).update("[dim]No balance data yet. Run: simledge sync[/]")
            summary_panel.border_title = "Current"
            self.query_one("#nw-summary", Static).update("[dim]No data[/]")
            self._refresh_cashflow(conn, account_ids)
            conn.close()
            return

        month_labels = [h["month"][5:] for h in history]
        values = [h["net_worth"] for h in history]

        w = max(40, self.app.size.width - 8)
        chart = render_line_chart(values, month_labels, width=w, height=12, color=GREEN)
        self.query_one("#nw-chart", Static).update(chart)
        chart_panel.border_title = f"Net Worth ({self._lookback}mo)"

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
        self._refresh_cashflow(conn, account_ids)
        conn.close()

    def _refresh_cashflow(self, conn, account_ids):
        cf_panel = self.query_one("#cf-panel")
        cf_chart = self.query_one("#cf-chart", Static)
        cf_summary_w = self.query_one("#cf-summary", Static)
        cf_warnings = self.query_one("#cf-warnings", Static)

        try:
            projection = project_balances(conn, days=90, account_ids=account_ids)
        except Exception:
            cf_panel.border_title = "Cash Flow Projection (90 days)"
            cf_chart.update("[dim]Projection unavailable[/]")
            cf_summary_w.update("")
            cf_warnings.update("")
            return

        daily = projection["daily_totals"]
        if not daily:
            cf_panel.border_title = "Cash Flow Projection (90 days)"
            cf_chart.update(
                "[dim]No recurring transactions detected — projection unavailable. "
                "Run sync to build transaction history.[/]"
            )
            cf_summary_w.update("")
            cf_warnings.update("")
            return

        # Check if there are any recurring transactions driving the projection
        summary = projection["summary"]
        has_changes = summary["current_total"] != summary["projected_90d"]

        cf_panel.border_title = "Cash Flow Projection (90 days)"

        # Chart data
        values = [d["projected_balance"] for d in daily]
        from datetime import datetime
        date_labels_full = []
        for d in daily:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            date_labels_full.append(dt.strftime("%b %-d"))
        w = max(40, self.app.size.width - 8)
        chart = render_line_chart(values, date_labels_full, width=w, height=12, color=TEAL)
        cf_chart.update(chart)

        # Summary line
        cur = summary["current_total"]
        p30 = summary["projected_30d"]
        p60 = summary["projected_60d"]
        p90 = summary["projected_90d"]

        if not has_changes:
            cf_summary_w.update(
                "[dim]No recurring transactions detected — projection unavailable. "
                "Run sync to build transaction history.[/]"
            )
            cf_warnings.update("")
            return

        change = p90 - cur
        pct = (change / abs(cur) * 100) if cur != 0 else 0
        change_color = "#22c55e" if change >= 0 else "#ef4444"

        lines = [
            f"Today: ${cur:,.0f}   30d: ${p30:,.0f}   60d: ${p60:,.0f}",
            f"90d:   ${p90:,.0f}   [{change_color}]Change: ${change:+,.0f} ({pct:+.1f}%)[/]",
        ]
        cf_summary_w.update("\n".join(lines))

        # Warnings
        neg = projection["negative_dates"][:3]
        if neg:
            warning_lines = []
            for nd in neg:
                warning_lines.append(
                    f"[#ef4444]⚠ {nd['date']}: {nd['account']} may go negative "
                    f"(${nd['balance']:,.2f})[/]"
                )
            cf_warnings.update("\n".join(warning_lines))
        else:
            cf_warnings.update("")
