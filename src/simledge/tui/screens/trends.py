"""Trends screen — monthly spending and income charts with category comparisons."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import (
    income_by_category,
    income_trend,
    spending_by_category_grouped,
    spending_trend,
    yoy_comparison,
)
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.charts import GREEN, TEAL, render_bar_chart, render_data_table
from simledge.tui.formatting import format_dollar
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
                yield Static("", id="spending-chart")
                yield Static("", id="spending-data-table")
            yield Vertical(
                Static("", id="comparison-content"), id="comparison-panel", classes="panel"
            )
            with Vertical(id="income-panel", classes="panel"):
                yield Static("", id="income-chart")
                yield Static("", id="income-data-table")
                yield Static("", id="income-sources")
            yield Vertical(
                Static("", id="yoy-category-content"), id="yoy-category-panel", classes="panel"
            )
            with Vertical(id="category-spending-panel", classes="panel"):
                yield Static("", id="category-spending-content")

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

    def on_resize(self, event):
        self._refresh_data()

    def _refresh_data(self):
        m = self.app.privacy_mode
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

        current_cats = spending_by_category_grouped(conn, current_month, account_ids=account_ids)
        prev_cats = spending_by_category_grouped(conn, prev_month, account_ids=account_ids)
        inc_trend = income_trend(conn, months=self._lookback, account_ids=account_ids)
        inc_cats = income_by_category(conn, current_month, account_ids=account_ids)
        yoy = yoy_comparison(conn, current_month, account_ids=account_ids)
        conn.close()

        # Spending chart
        if trend:
            month_labels = [t["month"][5:] for t in trend]
            values = [abs(t["total"]) for t in trend]
            w = max(40, self.app.size.width - 8)
            chart = render_bar_chart(values, month_labels, width=w, height=12, color=TEAL)
            self.query_one("#spending-chart", Static).update(chart)
            data_tbl = render_data_table(month_labels, values, width=w)
            self.query_one("#spending-data-table", Static).update(data_tbl)
            self.query_one("#chart-panel").border_title = f"Monthly Spending ({self._lookback}mo)"
        else:
            self.query_one("#chart-panel").border_title = f"Monthly Spending ({self._lookback}mo)"
            self.query_one("#spending-chart", Static).update("[dim]No data yet[/]")
            self.query_one("#spending-data-table", Static).update("")

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
                        f"{cat:<18} [bold]{format_dollar(abs(prev), masked=m):>10}[/] → [bold]{format_dollar(abs(cur), masked=m):>10}[/]  [{color}]{arrow} {abs(change):.0f}%[/]"
                    )
                else:
                    lines.append(
                        f"{cat:<18} {'':>11} → [bold]{format_dollar(abs(cur), masked=m):>10}[/]  [dim]new[/]"
                    )

        if not lines:
            lines.append("[dim]No comparison data yet. Run: simledge sync[/]")

        self.query_one("#comparison-content", Static).update("\n".join(lines))

        # Income panel
        self.query_one("#income-panel").border_title = f"Income ({self._lookback}mo)"
        if inc_trend:
            inc_labels = [t["month"][5:] for t in inc_trend]
            inc_values = [t["total"] for t in inc_trend]
            w = max(40, self.app.size.width - 8)
            chart = render_bar_chart(inc_values, inc_labels, width=w, height=12, color=GREEN)
            self.query_one("#income-chart", Static).update(chart)
            data_tbl = render_data_table(inc_labels, inc_values, width=w)
            self.query_one("#income-data-table", Static).update(data_tbl)
        else:
            self.query_one("#income-chart", Static).update("[dim]No income data yet[/]")
            self.query_one("#income-data-table", Static).update("")

        if inc_cats:
            total_inc = sum(c["total"] for c in inc_cats)
            max_total = inc_cats[0]["total"] if inc_cats else 1
            src_lines = []
            for c in inc_cats:
                cat = c["category"]
                amt = c["total"]
                pct = (amt / total_inc * 100) if total_inc else 0
                bar_width = 25
                filled = int(bar_width * (amt / max_total)) if max_total > 0 else 0
                bar = f"[#22c55e]{chr(0x2588) * filled}[/][#333]{chr(0x2591) * (bar_width - filled)}[/]"
                src_lines.append(
                    f"{cat:<18} [bold]{format_dollar(amt, masked=m):>10}[/]  {bar}  [dim]{pct:>5.1f}%[/]"
                )
            self.query_one("#income-sources", Static).update("\n".join(src_lines))
        else:
            self.query_one("#income-sources", Static).update("[dim]No income this month[/]")

        # YoY category comparison
        yoy_panel = self.query_one("#yoy-category-panel")
        has_prev = yoy["previous_spending"] != 0 or yoy["previous_income"] != 0
        if has_prev:
            prev_label = datetime.strptime(yoy["previous_month"], "%Y-%m").strftime("%b %Y")
            yoy_panel.border_title = f"vs. {prev_label} (by category)"
            yoy_panel.display = True
            ylines = []
            total_cur = 0
            total_prev = 0
            for c in yoy["categories"]:
                cur = abs(c["current"])
                prev = abs(c["previous"])
                total_cur += cur
                total_prev += prev
                if c["previous"] == 0:
                    ylines.append(
                        f"{c['category']:<14} {'':>7} \u2192 {format_dollar(cur, masked=m):>10}   [dim]new[/]"
                    )
                elif c["current"] == 0:
                    ylines.append(
                        f"{c['category']:<14} {format_dollar(prev, masked=m):>8} \u2192 {'':>10}   [dim]gone[/]"
                    )
                elif c["change_pct"] is not None:
                    pct = c["change_pct"]
                    if pct < 0:
                        arrow, color = "\u25bc", "#22c55e"
                    elif pct > 0:
                        arrow, color = "\u25b2", "#ef4444"
                    else:
                        arrow, color = "\u2014", "dim"
                    ylines.append(
                        f"{c['category']:<14} {format_dollar(prev, masked=m):>8} \u2192 {format_dollar(cur, masked=m):>10}   [{color}]{arrow} {abs(pct):.1f}%[/]"
                    )
            # Total line
            if total_prev > 0:
                total_pct = ((total_cur - total_prev) / total_prev) * 100
                if total_pct < 0:
                    t_arrow, t_color = "\u25bc", "#22c55e"
                elif total_pct > 0:
                    t_arrow, t_color = "\u25b2", "#ef4444"
                else:
                    t_arrow, t_color = "\u2014", "dim"
                ylines.append(
                    f"\n{'Total':<14} {format_dollar(total_prev, masked=m):>8} \u2192 {format_dollar(total_cur, masked=m):>10}   [{t_color}]{t_arrow} {abs(total_pct):.1f}%[/]"
                )
            self.query_one("#yoy-category-content", Static).update("\n".join(ylines))
        else:
            yoy_panel.display = False

        # Category spending breakdown
        cat_panel = self.query_one("#category-spending-panel")
        cat_panel.border_title = f"Spending by Category — {current_month[5:]}"

        if current_cats:
            total_spending = sum(abs(c["total"]) for c in current_cats)
            max_cat = max(abs(c["total"]) for c in current_cats) if current_cats else 1
            bar_width = 30
            cat_lines = []

            for group in current_cats:
                cat = group["category"]
                amt = abs(group["total"])
                pct = (amt / total_spending * 100) if total_spending else 0
                filled = int(bar_width * (amt / max_cat)) if max_cat > 0 else 0
                bar = f"[#2dd4bf]{chr(0x2588) * filled}[/][#333]{chr(0x2591) * (bar_width - filled)}[/]"
                cat_lines.append(
                    f"[bold]{cat:<18}[/] {format_dollar(amt, masked=m):>10}  {bar}  [dim]{pct:>5.1f}%[/]"
                )

                # Subcategories
                children = group.get("children", [])
                for child in children:
                    sub_name = child["category"].split(":", 1)[1] if ":" in child["category"] else child["category"]
                    sub_amt = abs(child["total"])
                    sub_pct = (sub_amt / total_spending * 100) if total_spending else 0
                    sub_filled = int(bar_width * (sub_amt / max_cat)) if max_cat > 0 else 0
                    sub_bar = f"[#1a9a8a]{chr(0x2588) * sub_filled}[/][#333]{chr(0x2591) * (bar_width - sub_filled)}[/]"
                    cat_lines.append(
                        f"  [dim]{sub_name:<16}[/] {format_dollar(sub_amt, masked=m):>10}  {sub_bar}  [dim]{sub_pct:>5.1f}%[/]"
                    )

            # Total line
            cat_lines.append(f"\n[bold]{'Total':<18}[/] {format_dollar(total_spending, masked=m):>10}")
            self.query_one("#category-spending-content", Static).update("\n".join(cat_lines))
        else:
            self.query_one("#category-spending-content", Static).update(
                "[dim]No spending data this month[/]"
            )
