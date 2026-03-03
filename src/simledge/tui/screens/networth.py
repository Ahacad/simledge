"""Net Worth screen — net worth over time with chart."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import net_worth_history
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


class NetWorthScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield NavBar("networth")
        with VerticalScroll():
            yield Static("", id="networth-chart")
            yield Static("", id="networth-content")
        yield Footer()

    def on_mount(self):
        conn = init_db(DB_PATH)
        history = net_worth_history(conn, months=12)
        conn.close()

        chart_widget = self.query_one("#networth-chart", Static)
        text_widget = self.query_one("#networth-content", Static)

        if not history:
            chart_widget.update("")
            text_widget.update("\n  No balance data yet. Run: simledge sync")
            return

        month_labels = [h["month"][5:] for h in history]
        values = [h["net_worth"] for h in history]

        # Chart — convert ANSI to Rich Text so Textual can render it
        if HAS_PLOTEXT and len(history) > 1:
            plt.clear_figure()
            x = list(range(len(month_labels)))
            plt.plot(x, values, marker="braille")
            plt.xticks(x, month_labels)
            plt.title("Net Worth Over Time")
            plt.theme("dark")
            plt.plotsize(60, 15)
            chart_widget.update(Text.from_ansi(plt.build()))
        else:
            chart_widget.update("")

        # Current + change
        lines = []
        current = values[-1] if values else 0
        lines.append(f"  Current Net Worth: ${current:,.2f}")

        if len(values) >= 2:
            prev = values[-2]
            change = current - prev
            pct = (change / abs(prev) * 100) if prev != 0 else 0
            arrow = "\u25b2" if change >= 0 else "\u25bc"
            color = "[green]" if change >= 0 else "[red]"
            lines.append(
                f"  30-day Change: {color}{arrow} ${abs(change):,.2f} ({pct:+.1f}%)[/]"
            )

        text_widget.update("\n".join(lines))
