"""Net Worth screen — net worth over time with chart."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import net_worth_history
from simledge.config import DB_PATH
from simledge.db import init_db

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


class NetWorthScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="networth-content")
        yield Footer()

    def on_mount(self):
        conn = init_db(DB_PATH)
        history = net_worth_history(conn, months=12)
        conn.close()

        lines = ["\n"]

        if not history:
            lines.append("  No balance data yet. Run: simledge sync")
            self.query_one("#networth-content", Static).update("\n".join(lines))
            return

        months = [h["month"][5:] for h in history]
        values = [h["net_worth"] for h in history]

        # Chart
        if HAS_PLOTEXT and len(history) > 1:
            plt.clear_figure()
            plt.plot(months, values, marker="braille")
            plt.title("Net Worth Over Time")
            plt.theme("dark")
            plt.plotsize(60, 15)
            lines.append(plt.build())
            lines.append("")

        # Current + change
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

        self.query_one("#networth-content", Static).update("\n".join(lines))
