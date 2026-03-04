"""Trends screen — monthly spending chart and category comparisons."""

from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import spending_trend, spending_by_category
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


class TrendsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("trends")
        with VerticalScroll():
            yield Static("", id="trends-chart")
            yield Static("", id="trends-content")

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

        chart_widget = self.query_one("#trends-chart", Static)
        text_widget = self.query_one("#trends-content", Static)

        # Chart — convert ANSI to Rich Text so Textual can render it
        if trend and HAS_PLOTEXT:
            month_labels = [t["month"][5:] for t in trend]
            values = [t["total"] for t in trend]
            plt.clear_figure()
            x = list(range(len(month_labels)))
            plt.bar(x, [abs(v) for v in values])
            plt.xticks(x, month_labels)
            plt.title("Monthly Spending")
            plt.theme("dark")
            plt.plotsize(60, 15)
            chart_widget.update(Text.from_ansi(plt.build()))
        else:
            chart_widget.update("")

        # Category comparison
        lines = []
        if current_cats or prev_cats:
            prev_dict = {c["category"]: c["total"] for c in prev_cats}
            lines.append(f"  Category Comparison ({prev_month[5:]} \u2192 {current_month[5:]})")
            separator = "\u2500" * 50
            lines.append(f"  {separator}")
            for c in current_cats:
                cat = c["category"]
                cur = c["total"]
                prev = prev_dict.get(cat, 0)
                if prev != 0:
                    change = ((cur - prev) / abs(prev)) * 100
                    arrow = "\u25b2" if change > 0 else "\u25bc"
                    lines.append(
                        f"  {cat:<18} ${abs(prev):>9,.2f} \u2192 ${abs(cur):>9,.2f}  {arrow} {abs(change):.0f}%"
                    )
                else:
                    dash = "\u2014"
                    lines.append(f"  {cat:<18} {dash:>11} \u2192 ${abs(cur):>9,.2f}  new")

        if not trend and not current_cats:
            lines.append("  No data yet. Run: simledge sync")

        text_widget.update("\n".join(lines))
