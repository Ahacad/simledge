"""Trends screen — monthly spending chart and category comparisons."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import spending_trend, spending_by_category
from simledge.config import DB_PATH
from simledge.db import init_db

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


def _render_chart(months, values):
    """Render a bar chart as a string using plotext."""
    if not HAS_PLOTEXT or not months:
        return "  No data or plotext not installed."

    plt.clear_figure()
    plt.bar(months, [abs(v) for v in values])
    plt.title("Monthly Spending")
    plt.theme("dark")
    plt.plotsize(60, 15)
    return plt.build()


class TrendsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="trends-content")
        yield Footer()

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

        lines = ["\n"]

        # Chart
        if trend:
            months = [t["month"][5:] for t in trend]  # MM only
            values = [t["total"] for t in trend]
            chart = _render_chart(months, values)
            lines.append(chart)
            lines.append("")

        # Category comparison
        if current_cats or prev_cats:
            prev_dict = {c["category"]: c["total"] for c in prev_cats}
            lines.append(f"  Category Comparison ({prev_month[5:]} \u2192 {current_month[5:]})")
            lines.append(f"  {'\u2500' * 50}")
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
                    lines.append(f"  {cat:<18} {'\u2014':>11} \u2192 ${abs(cur):>9,.2f}  new")

        if not trend and not current_cats:
            lines.append("  No data yet. Run: simledge sync")

        self.query_one("#trends-content", Static).update("\n".join(lines))
