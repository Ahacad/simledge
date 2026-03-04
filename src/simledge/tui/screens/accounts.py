"""Accounts screen — balances grouped by institution."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("accounts")
        yield VerticalScroll(id="accounts-scroll")

    def on_mount(self):
        conn = init_db(DB_PATH)
        accounts = account_summary(conn)
        conn.close()

        scroll = self.query_one("#accounts-scroll", VerticalScroll)

        if not accounts:
            panel = Vertical(Static("[dim]No accounts yet. Run: simledge sync[/]"), classes="panel")
            panel.border_title = "Accounts"
            scroll.mount(panel)
            return

        # Group by institution
        groups = {}
        total_assets = 0
        total_debt = 0
        for a in accounts:
            inst = a["institution"] or "Unknown"
            groups.setdefault(inst, []).append(a)
            bal = a["balance"] or 0
            if bal >= 0:
                total_assets += bal
            else:
                total_debt += bal

        for inst, accts in groups.items():
            lines = []
            for a in accts:
                bal = a["balance"] or 0
                color = "#22c55e" if bal >= 0 else "#ef4444"
                lines.append(f"{a['name']:<30} [{color}]${bal:>12,.2f}[/]")
            panel = Vertical(Static("\n".join(lines)), classes="panel")
            panel.border_title = inst
            scroll.mount(panel)

        # Summary panel
        net = total_assets + total_debt
        summary_lines = [
            f"[bold]Assets:[/]   [#22c55e]${total_assets:>12,.2f}[/]",
            f"[bold]Debt:[/]     [#ef4444]${total_debt:>12,.2f}[/]",
            f"[bold]Net Worth:[/] ${net:>12,.2f}",
        ]
        summary = Vertical(Static("\n".join(summary_lines)), classes="panel")
        summary.border_title = "Summary"
        scroll.mount(summary)
